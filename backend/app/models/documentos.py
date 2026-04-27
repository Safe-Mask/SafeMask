from sqlalchemy import Boolean, Column, Integer, String, TIMESTAMP, BIGINT, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Documento(Base):
    __tablename__ = "documentos"

    doc_id = Column(Integer, primary_key=True, index=True)
    user_team_id = Column(Integer, ForeignKey("usuario_equipe.user_team_id", ondelete="CASCADE"), nullable=False)
    nome_original = Column(String(255), nullable=False)
    extensao = Column(String(20), nullable=False)
    tamanho_bytes = Column(BIGINT, nullable=False)
    nivel_seguranca = Column(Integer, nullable=False)
    chave_criptografica = Column(String(255), nullable=False)
    hash_documento = Column(String(255), nullable=False)
    criado_em = Column(TIMESTAMP, server_default=func.now())
    caminho_storage = Column(String(500), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
    status_processamento = Column(String(50), nullable=False)

    usuario_equipe = relationship("UsuarioEquipe", back_populates="documentos")
    dados_sensiveis = relationship("DadoSensivel", back_populates="documento", cascade="all, delete-orphan")
