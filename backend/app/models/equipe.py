from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Equipe(Base):
    __tablename__ = "equipe"

    team_id = Column(Integer, primary_key=True, index=True)
    # Toda equipe pertence a uma organizacao. Nullable no schema para permitir
    # a migracao em bancos existentes; o app sempre preenche.
    organizacao_id = Column(
        Integer,
        ForeignKey("organizacao.organizacao_id"),
        nullable=True,
        index=True,
    )
    nome = Column(String(120), nullable=False)
    descricao = Column(Text)
    criado_em = Column(TIMESTAMP, server_default=func.now())

    organizacao = relationship("Organizacao", back_populates="equipes")

    # Relacionamento com UsuarioEquipe
    membros_assoc = relationship("UsuarioEquipe", back_populates="equipe", cascade="all, delete-orphan")
