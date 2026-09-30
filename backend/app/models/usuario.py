from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuario"

    user_id = Column(Integer, primary_key=True, index=True)
    organizacao_id = Column(
        Integer,
        ForeignKey("organizacao.organizacao_id"),
        nullable=True,
        index=True,
    )
    nome = Column(String(120), nullable=False)
    email = Column(String(129), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    # Sobe a cada troca de senha. O access token carrega o valor com que foi
    # emitido; um token anterior deixa de servir quando a versao muda. E o que
    # corta o acesso de quem roubou a senha antiga.
    token_version = Column(Integer, nullable=False, default=0, server_default="0")
    criado_em = Column(TIMESTAMP, server_default=func.now())

    organizacao = relationship("Organizacao", back_populates="usuarios")

    # Relacionamento com UsuarioEquipe
    equipes_assoc = relationship("UsuarioEquipe", back_populates="usuario", cascade="all, delete-orphan")
    logs_auditoria = relationship("LogAuditoria", back_populates="usuario", cascade="all, delete-orphan")

