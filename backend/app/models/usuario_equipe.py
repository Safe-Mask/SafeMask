from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class UsuarioEquipe(Base):
    __tablename__ = "usuario_equipe"

    user_team_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuario.user_id", ondelete="CASCADE"), nullable=False)
    team_id = Column(Integer, ForeignKey("equipe.team_id", ondelete="CASCADE"), nullable=False)
    cargo = Column(String(50), nullable=False)
    criado_em = Column(TIMESTAMP, server_default=func.now())

    usuario = relationship("Usuario", back_populates="equipes_assoc")
    equipe = relationship("Equipe", back_populates="membros_assoc")
    documentos = relationship("Documento", back_populates="usuario_equipe")