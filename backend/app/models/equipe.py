from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Equipe(Base):
    __tablename__ = "equipe"

    team_id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False, unique=True)
    criado_em = Column(TIMESTAMP, server_default=func.now())

    # Relacionamento com UsuarioEquipe
    membros_assoc = relationship("UsuarioEquipe", back_populates="equipe", cascade="all, delete-orphan")
