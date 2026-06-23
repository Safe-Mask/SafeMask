import os
import re
import bcrypt
import logging
import pdfplumber
import hashlib
import pytesseract
from PIL import Image, ImageDraw
from transformers import pipeline
from sqlalchemy.orm import Session
from pathlib import Path

from app.models.documentos import Documento
from app.models.dado_sensivel import DadoSensivel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DocumentScanner:
    def __init__(self, model_folder: str = None):
        if model_folder is None:
            model_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "safemask-ner")

        try:
            logger.info(f"Carregando IA customizada de {model_folder} ...")
            self.ia = pipeline(
                "token-classification",
                model=model_folder,
                tokenizer=model_folder,
                aggregation_strategy="simple"
            )
            logger.info("IA Carregada com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao carregar modelo de {model_folder}: {e}")
            raise

        self.regex_config = {
            "CPF": {"pattern": r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', "level": 2},
            "CNPJ": {"pattern": r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b', "level": 0},
            "EMAIL": {"pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "level": 1},
            "TELEFONE": {"pattern": r'\(?\d{2}\)?\s?9?\d{4}-?\d{4}', "level": 2},
            "RG": {"pattern": r'\b\d{1,2}\.?\d{3}\.?\d{3}-?[A-Za-z0-9]{1,2}(?:/[A-Z]{2})?\b|\b\d{7,9}\b', "level": 2},
            "PROCESSO": {"pattern": r'\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b|\b\d{3}/\d\.\d{2}\.\d{7}-\d\b', "level": 1},
            "DATA_NASC": {"pattern": r'\b\d{2}/\d{2}/\d{4}\b', "level": 1}
        }

    def _salvar_dado(self, db, doc_id, page, page_num, texto_secreto, entity_type, level, usando_ocr=False, ocr_data=None):
        salt = bcrypt.gensalt()
        valor_hash = bcrypt.hashpw(texto_secreto.encode('utf-8'), salt).decode('utf-8')
        salvos = 0
        coordenadas = []

        if usando_ocr and ocr_data:
            palavras_secreta = [p for p in texto_secreto.split() if len(p) > 2]

            for i, word in enumerate(ocr_data['text']):
                word_clean = word.strip(".,;:!?()[]")
                if word_clean and word_clean in palavras_secreta:
                    x0 = ocr_data['left'][i]
                    y0 = ocr_data['top'][i]
                    x1 = x0 + ocr_data['width'][i]
                    y1 = y0 + ocr_data['height'][i]
                    coord = [x0, y0, x1, y1]

                    dado = DadoSensivel(
                        doc_id=doc_id,
                        tipo_entidade=entity_type,
                        conteudo_hash=valor_hash,
                        pagina=page_num,
                        coordenadas=coord,
                        nivel_requerido=level
                    )
                    db.add(dado)
                    salvos += 1
                    coordenadas.append(coord)
        else:
            resultados = page.search(re.escape(texto_secreto))
            for res in resultados:
                coord = [res['x0'], res['top'], res['x1'], res['bottom']]
                dado = DadoSensivel(
                    doc_id=doc_id,
                    tipo_entidade=entity_type,
                    conteudo_hash=valor_hash,
                    pagina=page_num,
                    coordenadas=coord,
                    nivel_requerido=level
                )
                db.add(dado)
                salvos += 1
                coordenadas.append(coord)

        return salvos, coordenadas

    def scan_and_save(self, file_path: str, db: Session, user_team_id: int,
                      nome_original: str = None, nivel_seguranca: int = 1,
                      dir_original: Path = None, dir_censurado: Path = None) -> dict:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        doc_name = nome_original or os.path.basename(file_path)
        nome_sem_extensao, extensao = os.path.splitext(doc_name)
        tamanho = os.path.getsize(file_path)

        with open(file_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        chave_base = f"{file_hash}:{user_team_id}:{__import__('datetime').datetime.utcnow().isoformat()}"
        chave_cripto = hashlib.sha256(chave_base.encode()).hexdigest()

        novo_doc = Documento(
            user_team_id=user_team_id,
            nome_original=doc_name,
            extensao=extensao.replace('.', ''),
            tamanho_bytes=tamanho,
            nivel_seguranca=nivel_seguranca,
            chave_criptografica=chave_cripto,
            hash_documento=file_hash,
            caminho_storage="",
            status_processamento="PROCESSANDO"
        )

        db.add(novo_doc)
        db.flush()

        logger.info(f"Scan Iniciado: {doc_name} (ID: {novo_doc.doc_id})")
        sensitive_count = 0
        paginas_para_pdf = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                texto = page.extract_text()
                img_pagina = page.to_image(resolution=150)

                usando_ocr = False
                ocr_data = None

                if not texto or len(texto.strip()) < 20:
                    logger.info(f"Pagina {page_num} parece ser imagem. Ativando OCR...")
                    usando_ocr = True
                    texto = pytesseract.image_to_string(img_pagina.original, lang='por')
                    ocr_data = pytesseract.image_to_data(
                        img_pagina.original, lang='por', output_type=pytesseract.Output.DICT
                    )

                if not texto:
                    paginas_para_pdf.append(img_pagina.original.convert("RGB"))
                    continue

                segredos_encontrados = []

                for tipo, config in self.regex_config.items():
                    for match in re.finditer(config['pattern'], texto):
                        segredo = match.group()
                        if segredo not in segredos_encontrados:
                            count, coords = self._salvar_dado(
                                db, novo_doc.doc_id, page, page_num,
                                segredo, tipo, config['level'],
                                usando_ocr, ocr_data
                            )
                            sensitive_count += count
                            segredos_encontrados.append(segredo)

                            for c in coords:
                                if usando_ocr:
                                    draw = ImageDraw.Draw(img_pagina.original)
                                    draw.rectangle(c, fill="black")
                                else:
                                    img_pagina.draw_rect(c, fill="black", stroke=None)

                texto_limpo = texto
                for segredo in segredos_encontrados:
                    texto_limpo = texto_limpo.replace(segredo, " " * len(segredo))

                pedacos_texto = []
                pedaco_atual = ""
                for linha in texto_limpo.split('\n'):
                    if len(pedaco_atual) + len(linha) > 1000:
                        pedacos_texto.append(pedaco_atual)
                        pedaco_atual = linha + "\n"
                    else:
                        pedaco_atual += linha + "\n"
                if pedaco_atual:
                    pedacos_texto.append(pedaco_atual)

                for pedaco in pedacos_texto:
                    entidades_ia = self.ia(pedaco)

                    for ent in entidades_ia:
                        tipo_ia = ent['entity_group']
                        inicio = ent['start']
                        fim = ent['end']

                        while inicio > 0 and pedaco[inicio - 1] not in " \n\t([{":
                            inicio -= 1
                        while fim < len(pedaco) and pedaco[fim] not in " \n\t)]}.,;:!?":
                            fim += 1

                        palavra_exata = pedaco[inicio:fim].strip().strip(".,;:!?()[]")

                        ENTIDADES_NER = {
                            'PESSOA': (1, 'PESSOA'),
                            'ORGANIZACAO': (0, 'EMPRESA'),
                            'LOCAL': (0, 'LOCAL'),
                            'ENDERECO': (1, 'ENDERECO'),
                            'NUMERO_PROCESSO': (1, 'PROCESSO'),
                            'LEGISLACAO': (0, 'LEGISLACAO'),
                        }

                        if tipo_ia in ENTIDADES_NER and len(palavra_exata) > 2:
                            nivel, tipo_banco = ENTIDADES_NER[tipo_ia]
                            if palavra_exata not in segredos_encontrados:
                                if tipo_ia == 'PESSOA':
                                    nivel = 1
                                    tipo_banco = 'PESSOA'
                                else:
                                    nivel = 0
                                    tipo_banco = 'EMPRESA'

                                count, coords = self._salvar_dado(
                                    db, novo_doc.doc_id, page, page_num,
                                    palavra_exata, tipo_banco, nivel,
                                    usando_ocr, ocr_data
                                )
                                sensitive_count += count
                                segredos_encontrados.append(palavra_exata)

                                for c in coords:
                                    if usando_ocr:
                                        draw = ImageDraw.Draw(img_pagina.original)
                                        draw.rectangle(c, fill="black")
                                    else:
                                        img_pagina.draw_rect(c, fill="black", stroke=None)

                if usando_ocr:
                    paginas_para_pdf.append(img_pagina.original.convert("RGB"))
                else:
                    paginas_para_pdf.append(img_pagina.annotated.convert("RGB"))

        logger.info(f"Total de segredos encontrados: {sensitive_count}")

        if paginas_para_pdf and dir_censurado:
            dir_censurado.mkdir(parents=True, exist_ok=True)
            nome_tarjado = f"{file_hash}_tarjado.pdf"
            caminho_tarjado = dir_censurado / nome_tarjado

            for img in paginas_para_pdf:
                img.info = {}

            paginas_para_pdf[0].save(
                str(caminho_tarjado),
                format="PDF",
                save_all=True,
                append_images=paginas_para_pdf[1:]
            )

            logger.info(f"PDF tarjado gerado em: {caminho_tarjado}")

            novo_doc.caminho_storage = str(caminho_tarjado)
            novo_doc.status_processamento = "CONCLUIDO"
        else:
            novo_doc.status_processamento = "ERRO"
            logger.error("Nenhuma pagina processada para gerar PDF tarjado.")

        return {
            "doc_id": novo_doc.doc_id,
            "hash": file_hash,
            "caminho_censurado": novo_doc.caminho_storage,
            "total_sensiveis": sensitive_count,
            "status": novo_doc.status_processamento
        }
