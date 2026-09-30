from sqlalchemy import TIMESTAMP, Column, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Organizacao(Base):
    """Tenant raiz.

    A organizacao e o limite de isolamento: equipes e usuarios pertencem a
    exatamente uma, e nada de outra organizacao deve ser visivel. O SRS nao
    define esse conceito; ele existe para que duas empresas no mesmo deploy
    nao enxerguem os documentos uma da outra.
    """

    __tablename__ = "organizacao"

    organizacao_id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    criado_em = Column(TIMESTAMP, server_default=func.now())

    equipes = relationship("Equipe", back_populates="organizacao")
    usuarios = relationship("Usuario", back_populates="organizacao")
