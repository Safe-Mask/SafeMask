from sqlalchemy import Column, Integer, String, Text
from app.database import Base

class Cargo(Base):
    __tablename__ = "cargo"

    cargo_id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), nullable=False, unique=True)
    nivel = Column(Integer, nullable=False)
    descricao = Column(Text)