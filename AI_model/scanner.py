import spacy
import fitz
import re
import bcrypt # Ótima adição de segurança!
import os 
import logging
from sqlalchemy.orm import sessionmaker
from models import engine, Document, SensitiveData

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DocumentScanner:
    def __init__(self, model_name: str = "pt_core_news_lg"):
        try: 
            logger.info(f"🧠 Carregando IA {model_name} ...")
            self.nlp = spacy.load(model_name)
            logger.info("✅ IA Carregada")
        except OSError:
            logger.error(f"❌ Modelo '{model_name}' não instalado")
            raise

    def scan_and_save(self, file_path: str, user_id: int):
        Session = sessionmaker(bind=engine)
        session = Session()

        try: 
            if not os.path.exists(file_path):
                logger.error(f"Arquivo não encontrado: {file_path}")
                return

            doc_name = os.path.basename(file_path)

            # Cria o documento no banco
            novo_doc = Document(filename=doc_name, filepath=file_path, owner_id=user_id)
            session.add(novo_doc)
            session.commit()
            
            logger.info(f"📂 Scan Iniciado: {doc_name} (ID: {novo_doc.id})")
            
            pdf = fitz.open(file_path)
            sensitive_count = 0

            # Configuração REGEX
            regex_config = {
                "CPF": {"pattern": r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b', "level": 2},
                "CNPJ": {"pattern": r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b', "level": 0},
                "EMAIL": {"pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "level": 1},
                "TELEFONE": {"pattern": r'\(?\d{2}\)?\s?9?\d{4}-?\d{4}', "level": 2}
            }  
            
            for page_num, page in enumerate(pdf):
                text = page.get_text()

                # --- PARTE 1: REGEX (Matemática) ---
                for tipo, config in regex_config.items():
                    for match in re.finditer(config['pattern'], text):
                        valor_encontrado = match.group()
                        
                        # Criptografia (Hash)
                        salt = bcrypt.gensalt()
                        valor_hash = bcrypt.hashpw(valor_encontrado.encode('utf-8'), salt).decode('utf-8')
                        
                        areas = page.search_for(valor_encontrado)
                        for rect in areas:
                            dado = SensitiveData(
                                document_id=novo_doc.id,
                                entity_type=tipo,
                                original_content_encrypted=valor_hash,
                                page=page_num, # <--- Importante para o Redator saber a página
                                coordinates=[rect.x0, rect.y0, rect.x1, rect.y1],
                                required_level=config['level']
                            )
                            session.add(dado)
                            sensitive_count += 1
                
                # --- PARTE 2: IA / NLP (Inteligência) ---
                doc_nlp = self.nlp(text)
                
                for ent in doc_nlp.ents:
                    if len(ent.text.strip()) < 3: continue

                    tipo_ia = None 
                    nivel_ia = 0
                    
                    # Correção: Use ent.label_ (com underline) para pegar a string
                    if ent.label_ == "PER": 
                        tipo_ia = "PESSOA"
                        nivel_ia = 1 
                    elif ent.label_ == "ORG":
                        tipo_ia = "EMPRESA"
                        nivel_ia = 0
                    elif ent.label_ == "LOC":
                        tipo_ia = "LOCAL"
                        nivel_ia = 1
                    
                    if tipo_ia: 
                        # Hash para a IA também
                        salt = bcrypt.gensalt()
                        valor_ia_hash = bcrypt.hashpw(ent.text.encode('utf-8'), salt).decode('utf-8')

                        areas = page.search_for(ent.text)
                        for rect in areas:
                            dado = SensitiveData(
                                document_id=novo_doc.id,
                                entity_type=tipo_ia,
                                original_content_encrypted=valor_ia_hash, # Adicionado
                                page=page_num, # Adicionado
                                coordinates=[rect.x0, rect.y0, rect.x1, rect.y1],
                                required_level=nivel_ia # Correção: usa nivel_ia, não config
                            )
                            session.add(dado)
                            sensitive_count += 1

            session.commit()
            logger.info(f"✅ Sucesso! Total de segredos encontrados: {sensitive_count}") 

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Erro crítico: {e}")
        finally:
            session.close()
            if 'pdf' in locals(): pdf.close()

if __name__ == "__main__":
    # Cria PDF de teste
    nome_arquivo = "teste_ia.pdf"
    if not os.path.exists(nome_arquivo):
        print("📄 Criando PDF de teste...")
        doc = fitz.open()
        page = doc.new_page()
        texto = "O funcionário Lucas Silva (CPF 123.456.789-00) trabalha na Google Brasil."
        page.insert_text((50, 50), texto, fontsize=12)
        doc.save(nome_arquivo)
    
    # Roda scanner
    scanner = DocumentScanner()
    scanner.scan_and_save(nome_arquivo, user_id=1)