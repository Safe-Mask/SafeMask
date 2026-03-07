from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

from app.models.usuario_equipe import UsuarioEquipe

class Equipe(Base):
    __tablename__ = "equipe"

    team_id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False, unique=True)
    criado_em = Column(TIMESTAMP, server_default=func.now())

    membros_assoc = relationship("UsuarioEquipe", back_populates="equipe", cascade="all, delete-orphan")
    membros = relationship("Usuario", secondary="usuario_equipe", back_populates="equipes")
    documentos = relationship("Documento", back_populates="usuario_equipe")
