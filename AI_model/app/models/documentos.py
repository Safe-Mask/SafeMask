from sqlalchemy import Column, Integer, String, TIMESTAMP, BIGINT, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Documento(Base):
    __tablename__ = "documentos"

    doc_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuario.user_id"), nullable=False)
    nome_original = Column(String(255), nullable=False)
    extensao = Column(String(20), nullable=False)
    tamanho_bytes = Column(BIGINT, nullable=False)
    nivel_seguranca = Column(Integer, nullable=False)
    chave_criptografica = Column(String(255), nullable=False)
    hash_documento = Column(String(255), nullable=False)
    criado_em = Column(TIMESTAMP, server_default=func.now())

    usuario = relationship("Usuario", back_populates="documentos")
