from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class DadoSensivel(Base):
    __tablename__ = "dado_sensivel"

    sensivel_id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("documentos.doc_id", ondelete="CASCADE"), nullable=False)
    tipo_entidade = Column(String(50), nullable=False)
    conteudo_hash = Column(Text, nullable=False)
    pagina = Column(Integer, nullable=False)
    coordenadas = Column(JSONB, nullable=False)
    nivel_requerido = Column(Integer, nullable=False, default=4, server_default="4")

    documento = relationship("Documento", back_populates="dados_sensiveis")
