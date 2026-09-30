import hashlib
import json
import logging
import os
import re
from pathlib import Path

import bcrypt
import pdfplumber
import pytesseract
from PIL import ImageDraw
from sqlalchemy.orm import Session

from app.models.dado_sensivel import DadoSensivel
from app.models.documentos import Documento
from scanner.coordenadas import (
    ESPACO_PDF,
    ESPACO_PIXEL,
    aplicar_margem,
    normalizar,
    para_pontos,
)
from scanner.patterns import (
    CID10_PATTERN,
    CNS_PATTERN,
    CPF_PATTERN,
    CRM_PATTERN,
    EMAIL_PATTERN,
    PHONE_PATTERN,
    increment_cpf_count,
    mask_cpf,
    mask_phone,
)
from scanner.redaction import draw_structured_mask

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class NenhumaMascaraAplicavel(ValueError):
    """Havia o que cobrir, mas nenhuma caixa foi utilizavel.

    Distincto de um erro generico porque o destino nao e 500: o certo e servir
    a versao integralmente censurada. Devolver o original aqui seria o pior
    resultado possivel — o usuario pediu a versao parcial e receberia o
    documento sem nenhuma tarja.
    """


def _desempacotar_caixa(item) -> tuple:
    """(coordenadas, espaco) a partir do que a rota montou.

    Aceita a forma antiga (so a coordenada), em que o espaco e `pdf`.
    """
    if (isinstance(item, list | tuple) and len(item) == 2
            and isinstance(item[1], str)):
        return list(item[0]), item[1]
    return list(item), ESPACO_PDF


# (nivel_requerido, tipo_entidade) por entidade do NER.
#
# `nivel_requerido` e o cargo minimo que enxerga o dado: 1 supervisor+ ve tudo,
# 3 so o lider. Onde o regex ja cobre o mesmo dado, o nivel e o MESMO, para
# que o mesmo CPF chegue com o mesmo nivel seja encontrado por regex ou pelo
# NER — senao a mesma entidade teria dois niveis e a descensura_partial ficaria
# dependente de qual detector/views primeiro.
MAPA_ENTIDADES_NER = {
    'PESSOA': (2, 'PESSOA'),
    'ORGANIZACAO': (1, 'EMPRESA'),
    'LOCAL': (1, 'LOCAL'),
    'ENDERECO': (2, 'ENDERECO'),
    'CEP': (1, 'ENDERECO'),
    'NUMERO_PROCESSO': (1, 'PROCESSO'),
    'LEGISLACAO': (1, 'LEGISLACAO'),
    'JURISPRUDENCIA': (1, 'JURISPRUDENCIA'),
    'EVENTO': (1, 'EVENTO'),
    'TEMPO': (1, 'TEMPO'),
    'VALOR': (2, 'VALOR'),
    'CPF': (3, 'CPF'),
    'CNPJ': (1, 'CNPJ'),
    'TELEFONE': (2, 'TELEFONE'),
    'EMAIL': (2, 'EMAIL'),
    'RG': (3, 'RG'),
    'CNH': (3, 'CNH'),
    'PLACA_VEICULO': (2, 'PLACA'),
    'DATA_NASCIMENTO': (2, 'DATA_NASC'),
}

# Entidades que o modelo emite e que nao entram no mapa. `TEMPO` e `VALOR`
# guardam nivel 1/2; `''` e o rotulo que o tokenizer usa para token sem
# entidade. Nenhuma outra pode ser somada aqui sem escrever o motivo: entidade
# treinada e descartada em silencio e o tipo de bug que so aparece quando o
# documento some da tela de alguém.
# {"": "rotulo vazio do tokenizer"}
ENTIDADES_DESCARTADAS = {
    "": "rotulo vazio do tokenizer",
}


def entidades_saidas_do_modelo(model_folder: str = None) -> set:
    """Rótulos de entidade que o modelo carregado pode emitir."""
    if model_folder is None:
        model_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "safemask-ner")
    caminho = os.path.join(model_folder, "config.json")
    if not os.path.exists(caminho):
        return set()
    try:
        with open(caminho, encoding="utf-8") as fh:
            config = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return set()

    rotulos = set()
    for rotulo in config.get("id2label", {}).values():
        # "B-PESSOA" / "I-PESSOA" -> "PESSOA"
        partes = str(rotulo).split("-", 1)
        if len(partes) == 2:
            rotulos.add(partes[1])
    return rotulos


def entidades_sem_mapa(model_folder: str = None) -> set:
    """Entidades que o modelo emite e que nenhuma regra aceita.

    Vira um erro em vez de um silencio: se um retraining acrescentar uma
    entidade, o scanner precisa avisar.
    """
    Known = set(MAPA_ENTIDADES_NER) | set(ENTIDADES_DESCARTADAS)
    return {e for e in entidades_saidas_do_modelo(model_folder)
            if e and e not in Known}


def configuracoes_regex() -> dict:
    """Padroes e nivel de cada entidade detectavel por regex.

    Fora da classe de proposito: ler os niveis nao deve exigir carregar o
    modelo NER (centenas de MB), e e assim que o teste de paridade entre regex
    e NER consegue verificar sem instanciar o scanner.
    """
    return {
        "CPF": {"pattern": CPF_PATTERN.pattern, "level": 3},
        "CNPJ": {"pattern": r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b', "level": 1},
        "EMAIL": {"pattern": EMAIL_PATTERN.pattern, "level": 2},
        "TELEFONE": {"pattern": PHONE_PATTERN.pattern, "level": 2},
        "CNS": {"pattern": CNS_PATTERN.pattern, "level": 3},
        "CID10": {"pattern": CID10_PATTERN.pattern, "level": 3},
        "CRM": {"pattern": CRM_PATTERN.pattern, "level": 3},
        "RG": {"pattern": r'\b\d{1,2}\.?\d{3}\.?\d{3}-?[A-Za-z0-9]{1,2}(?:/[A-Z]{2})?\b|\b\d{7,9}\b', "level": 3},
        "PROCESSO": {"pattern": r'\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b|\b\d{3}/\d\.\d{2}\.\d{7}-\d\b', "level": 1},
        "DATA_NASC": {"pattern": r'\b\d{2}/\d{2}/\d{4}\b', "level": 2},
    }


class DocumentScanner:
    def __init__(self, model_folder: str = None):
        if model_folder is None:
            model_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "safemask-ner")

        self.ia = None
        modelo_existe = os.path.exists(os.path.join(model_folder, "model.safetensors")) or \
            os.path.exists(os.path.join(model_folder, "pytorch_model.bin"))

        if not modelo_existe:
            logger.warning(
                f"Pesos do modelo NER nao encontrados em {model_folder}. "
                "Rodando apenas com deteccao por regex."
            )
        else:
            try:
                logger.info(f"Carregando IA customizada de {model_folder} ...")
                # Import tardio: `transformers` arrasta torch (centenas de MB) e
                # baixa a memoria do container mesmo quando o NER nao e usado.
                from transformers import pipeline

                self.ia = pipeline(
                    "token-classification",
                    model=model_folder,
                    tokenizer=model_folder,
                    aggregation_strategy="simple"
                )
                logger.info("IA Carregada com sucesso!")
            except Exception as e:
                logger.error(f"Erro ao carregar modelo de {model_folder}: {e}")
                self.ia = None
                logger.warning("Rodando apenas com deteccao por regex.")

        sem_mapa = entidades_sem_mapa(model_folder)
        if sem_mapa:
            logger.warning(
                "Modelo emite entidade(s) sem regra no scanner, descartada(s): "
                f"{sorted(sem_mapa)}. Treine de novo ou acrescente a "
                "MAPA_ENTIDADES_NER."
            )

        self.regex_config = configuracoes_regex()

    def _salvar_dado(self, db, doc_id, page, page_num, texto_secreto, entity_type, level, usando_ocr=False, ocr_data=None):
        """Persiste um dado sensivel e devolve (salvos, coordenadas).

        `page` e a pagina do pdfplumber; `ocr_data` as caixas do tesseract. As
        coordenadas sao gravadas em um unico espaco, declarado em
        `espaco_coordenadas`, porque so a descensura parcial as le de volta e
        precisa saber se sao pontos ou pixels.
        """
        salt = bcrypt.gensalt()
        valor_hash = bcrypt.hashpw(texto_secreto.encode('utf-8'), salt).decode('utf-8')
        salvos = 0
        coordenadas = []

        if usando_ocr and ocr_data:
            espaco = ESPACO_PIXEL
            largura_pagina = float(page.width)
            altura_pagina = float(page.height)
            palavras_secreta = {p for p in texto_secreto.split() if len(p) > 2}

            for i, word in enumerate(ocr_data['text']):
                word_clean = word.strip(".,;:!?()[]")
                if not word_clean or word_clean not in palavras_secreta:
                    continue

                x0 = ocr_data['left'][i]
                y0 = ocr_data['top'][i]
                x1 = x0 + ocr_data['width'][i]
                y1 = y0 + ocr_data['height'][i]

                self._salvar_caixa(
                    db, doc_id, page_num, entity_type, valor_hash, level, espaco,
                    [x0, y0, x1, y1], largura_pagina, altura_pagina,
                    coordenadas,
                )
        else:
            espaco = ESPACO_PDF
            largura_pagina = float(page.width)
            altura_pagina = float(page.height)

            for res in page.search(re.escape(texto_secreto)):
                self._salvar_caixa(
                    db, doc_id, page_num, entity_type, valor_hash, level, espaco,
                    [res['x0'], res['top'], res['x1'], res['bottom']],
                    largura_pagina, altura_pagina,
                    coordenadas,
                )

        return salvos, coordenadas

    def _salvar_caixa(self, db, doc_id, page_num, entity_type, valor_hash, level,
                      espaco, coord, largura_pagina, altura_pagina, acumulador):
        """Grava uma caixa so depois de confirmar que ela cobre algo.

        Uma caixa degenerada (largura ou altura zero, coordenadas invertidas,
        ou wholly fora da pagina) nao protege nada e so polui a tabela — mas o
        pior efeito e silencioso: ela entra no `itens_para_cobrir` da
        descensura parcial e faz o gerador reprojetar um valor invalido.
        """
        if normalizar(coord, espaco, largura_pagina, altura_pagina) is None:
            return
        db.add(
            DadoSensivel(
                doc_id=doc_id,
                tipo_entidade=entity_type,
                conteudo_hash=valor_hash,
                pagina=page_num,
                coordenadas=[round(float(v), 3) for v in coord],
                espaco_coordenadas=espaco,
                nivel_requerido=level,
            )
        )
        acumulador.append(list(coord))

    def _desenhar_caixa_pil(
        self,
        img_pagina,
        coord: list,
        structured_mask: str | None = None,
        espaco: str = ESPACO_PDF,
    ):
        """Cobre uma coordenada com tarja preta ou máscara estruturada.

        O pdfplumber.drawing (wand/ImageMagick) pode estar ausente e nao desenhar
        nada silenciosamente; aqui convertemos as coords para pixels da imagem
        renderizada e desenhamos com ImageDraw (PIL).

        `espaco` diz se `coord` ja esta em pixels (OCR) ou em pontos do PDF.
        """
        try:
            pontos = aplicar_margem(para_pontos(coord, espaco), ESPACO_PDF)
        except ValueError:
            return
        x0, top, x1, bottom = pontos
        px0, ptop = img_pagina._reproject((x0, top))
        px1, pbottom = img_pagina._reproject((x1, bottom))

        if structured_mask:
            draw_structured_mask(
                img_pagina.original,
                (px0, ptop, px1, pbottom),
                structured_mask,
            )
            return

        ImageDraw.Draw(img_pagina.original).rectangle(
            [px0, ptop, px1, pbottom], fill="black"
        )

    def scan_and_save(self, file_path: str, db: Session, user_team_id: int,
                      nome_original: str = None, nivel_seguranca: int = 1,
                      dir_original: Path = None, dir_censurado: Path = None) -> dict:
        """Escaneia e persiste, garantindo que o Documento nao fique pendurado.

        Um PDF corrompido, um tesseract ausente ou um erro de OCR no meio do
        processamento levantavam excecao DEPOIS do `Documento` ja gravado com
        `status_processamento='PROCESSANDO'`. A rota de upload respondia
        sucesso, o documento aparecia na lista para sempre sem PDF censurado e
        sem caminho — o pior estado possivel: visivel e inutilizavel.

        Aqui a excecao marca ERRO e segue; quem chama decide a resposta.
        """
        try:
            return self._scan(file_path, db, user_team_id, nome_original,
                              nivel_seguranca, dir_original, dir_censurado)
        except Exception:
            self._marcar_erro(db, user_team_id, nome_original or file_path)
            raise

    def _marcar_erro(self, db: Session, user_team_id: int, doc_name: str):
        """Marca o ultimo Documento do usuario como ERRO, se ele existir.

        `commit=False`: quem chamou esta numa transacao que ainda vai tratar o
        erro; commitar aqui esconderia a falha do chamador.
        """
        documento = (
            db.query(Documento)
            .filter(
                Documento.user_team_id == user_team_id,
                Documento.nome_original == doc_name,
                Documento.status_processamento == "PROCESSANDO",
            )
            .order_by(Documento.doc_id.desc())
            .first()
        )
        if documento:
            documento.status_processamento = "ERRO"
            db.flush()
            logger.error(f"Documento {documento.doc_id} marcado como ERRO.")

    def _scan(self, file_path: str, db: Session, user_team_id: int,
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
            status_processamento="PROCESSANDO",
            cpf_censurados=0,
        )

        db.add(novo_doc)
        db.flush()

        logger.info(f"Scan Iniciado: {doc_name} (ID: {novo_doc.doc_id})")
        sensitive_count = 0
        cpf_censored_count = 0
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
                            cpf_censored_count = increment_cpf_count(
                                cpf_censored_count,
                                tipo,
                                count,
                            )
                            segredos_encontrados.append(segredo)

                            structured_mask = (
                                mask_cpf(segredo)
                                if tipo == "CPF"
                                else mask_phone(segredo)
                                if tipo == "TELEFONE"
                                else None
                            )
                            espaco = ESPACO_PIXEL if usando_ocr else ESPACO_PDF
                            for c in coords:
                                self._desenhar_caixa_pil(
                                    img_pagina,
                                    c,
                                    structured_mask=structured_mask,
                                    espaco=espaco,
                                )

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
                    if not self.ia:
                        continue
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

                        if tipo_ia in MAPA_ENTIDADES_NER and len(palavra_exata) > 2:
                            nivel, tipo_banco = MAPA_ENTIDADES_NER[tipo_ia]
                            if palavra_exata not in segredos_encontrados:
                                count, coords = self._salvar_dado(
                                    db, novo_doc.doc_id, page, page_num,
                                    palavra_exata, tipo_banco, nivel,
                                    usando_ocr, ocr_data
                                )
                                sensitive_count += count
                                segredos_encontrados.append(palavra_exata)

                                espaco = ESPACO_PIXEL if usando_ocr else ESPACO_PDF
                                for c in coords:
                                    self._desenhar_caixa_pil(img_pagina, c, espaco=espaco)

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

        novo_doc.cpf_censurados = cpf_censored_count

        return {
            "doc_id": novo_doc.doc_id,
            "hash": file_hash,
            "caminho_censurado": novo_doc.caminho_storage,
            "total_sensiveis": sensitive_count,
            "cpf_censurados": cpf_censored_count,
            "status": novo_doc.status_processamento
        }

    def gerar_pdf_parcial(self, file_path: str, itens_para_cobrir: dict,
                          dir_destino: Path, nome_saida: str) -> Path:
        """Regera um PDF a partir do original, tapando so o que deve ficar tapado.

        itens_para_cobrir: dict {numero_pagina: [(coordenadas, espaco)]}. O
        espaco vem de `DadoSensivel.espaco_coordenadas`: sem ele, as caixas de
        uma pagina escaneada (pixels) eram reprojetadas como pontos do PDF e a
        tarja saia deslocada — o dado ficava visivel e outra area era coberta.
        Aceita tambem a coordenada "solta", assumindo `pdf`, que e o espaco de
        tudo que foi gravado antes desta coluna existir.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo nao encontrado: {file_path}")

        total_caixas = sum(len(v) for v in itens_para_cobrir.values())

        paginas_para_pdf = []
        aplicadas = 0
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                img_pagina = page.to_image(resolution=150)
                largura, altura = float(page.width), float(page.height)
                descartadas = 0

                for item in itens_para_cobrir.get(page_num, []):
                    coord, espaco = _desempacotar_caixa(item)
                    util = normalizar(coord, espaco, largura, altura)
                    if util is None:
                        descartadas += 1
                        continue
                    self._desenhar_caixa_pil(img_pagina, coord, espaco=espaco)
                    aplicadas += 1

                if descartadas:
                    logger.warning(
                        f"Pagina {page_num}: {descartadas} caixa(s) invalida(s) "
                        "ignorada(s) na descensura parcial."
                    )
                paginas_para_pdf.append(img_pagina.original.convert("RGB"))

        if not paginas_para_pdf:
            raise ValueError("Nenhuma pagina disponivel para gerar o PDF parcial.")

        # Havia o que cobrir e nada foi coberto: devolver o PDF assim seria
        # entregar o original sem nenhuma tarja.
        if total_caixas and aplicadas == 0:
            raise NenhumaMascaraAplicavel(
                f"{total_caixas} caixa(s) solicitada(s), nenhuma utilizavel."
            )

        dir_destino.mkdir(parents=True, exist_ok=True)
        caminho_parcial = dir_destino / nome_saida

        for img in paginas_para_pdf:
            img.info = {}

        paginas_para_pdf[0].save(
            str(caminho_parcial),
            format="PDF",
            save_all=True,
            append_images=paginas_para_pdf[1:]
        )
        logger.info(f"PDF parcial gerado em: {caminho_parcial}")
        return caminho_parcial
