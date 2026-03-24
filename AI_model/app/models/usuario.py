from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Usuario(Base):
    __tablename__ = "usuario"

    user_id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(129), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    criado_em = Column(TIMESTAMP, server_default=func.now())

    documentos = relationship("Documento", back_populates="usuario", cascade="all, delete-orphan")

