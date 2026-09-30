from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class DadoSensivel(Base):
    __tablename__ = "dado_sensivel"

    sensivel_id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("documentos.doc_id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_entidade = Column(String(50), nullable=False)
    conteudo_hash = Column(Text, nullable=False)
    pagina = Column(Integer, nullable=False)
    coordenadas = Column(JSONB, nullable=False)
    # Em que espaco `coordenadas` estao expressas. Uma pagina lida por texto
    # devolve pontos do PDF; uma pagina tratada por OCR devolve pixels da
    # imagem renderizada (150 dpi). Sem distinguir, a descensura parcial
    # reprojeta pixels como pontos e a tarja cai fora do lugar.
    espaco_coordenadas = Column(String(10), nullable=False, default="pdf",
                               server_default="pdf")
    nivel_requerido = Column(Integer, nullable=False, default=4, server_default="4")

    documento = relationship("Documento", back_populates="dados_sensiveis")
