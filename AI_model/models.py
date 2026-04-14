import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from dotenv import load_dotenv
load_dotenv()

senha = os.getenv('DB_PASS')
usuario = os.getenv('DB_USER')
banco = os.getenv('DB_NAME')

DATABASE_URL = f"postgresql://{usuario}:{senha}@localhost:5432/{banco}"

engine = create_engine(DATABASE_URL)
Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuario"

    user_id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(129), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    criado_em = Column(TIMESTAMP, server_default=func.now())

    # Relacionamento com UsuarioEquipe
    equipes_assoc = relationship("UsuarioEquipe", back_populates="usuario", cascade="all, delete-orphan")


class Documento(Base):
    __tablename__ = "documentos"

    doc_id = Column(Integer, primary_key=True, index=True)
    user_team_id = Column(Integer, ForeignKey("usuario_equipe.user_team_id"), nullable=False)
    nome_original = Column(String(255), nullable=False)
    extensao = Column(String(20), nullable=False)
    tamanho_bytes = Column(BIGINT, nullable=False)
    caminho_storage = Column(String(500), nullable=False) # Ex: "/home/lucas/pdfs/123.pdf" ou "s3://meu-bucket/123.pdf"
    nivel_seguranca = Column(Integer, nullable=False)
    chave_criptografica = Column(String(255), nullable=False)
    hash_documento = Column(String(255), nullable=False)
    criado_em = Column(TIMESTAMP, server_default=func.now())

    ativo = Column(Boolean, default=True, nullable=False) # Soft Delete
    status_processamento = Column(String(50), default="PENDENTE") # PENDENTE, PROCESSANDO, CONCLUIDO, ERRO

    usuario_equipe = relationship("UsuarioEquipe", back_populates="documentos")
    dados_sensiveis = relationship("DadoSensivel", back_populates="documento", cascade="all, delete-orphan")

class DadoSensivel(Base):
    __tablename__ = "dado_sensivel"

    sensivel_id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("documentos.doc_id", ondelete="CASCADE"), nullable=False)
    
    tipo_entidade = Column(String(50), nullable=False) # Ex: CPF, CNPJ, NOME_PESSOA
    conteudo_hash = Column(Text, nullable=False) # O texto original criptografado (Bcrypt)
    pagina = Column(Integer, nullable=False) # Em qual página a tarja vai ficar
    coordenadas = Column(JSON, nullable=False) # [x0, y0, x1, y1] - Onde desenhar a tarja
    nivel_requerido = Column(Integer, default=4) # Nível do Cargo necessário para ver sem a tarja

    documento = relationship("Documento", back_populates="dados_sensiveis")

class LogAuditoria(Base):
    __tablename__ = "log_auditoria"

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuario.user_id"), nullable=False)
    doc_id = Column(Integer, ForeignKey("documentos.doc_id"), nullable=True) # Pode ser null se a ação for só "LOGIN"
    
    acao = Column(String(100), nullable=False) # Ex: "VISUALIZOU_COM_TARJA", "BAIXOU_ORIGINAL", "DELETOU_DOC"
    ip_origem = Column(String(45), nullable=False) # Endereço IP de quem fez a requisição
    data_hora = Column(TIMESTAMP, server_default=func.now())
################
### Execução ###
################ 
if __name__ == "__main__" :
    try :
        print("Conectando ao PostgreSQL")
        Base.metadata.create_all(engine)
        print('Tabelas Criadas com sucesso')
        print(" - Tabela 'users' criada")
        print(" - Tabela 'documents' criada")
        print(" - Tabela 'sensitive_data_map' criada")
    except Exception as e :
        print("Erro ao Criar as tabelas")
        print(e)

