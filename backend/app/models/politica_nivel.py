from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class PoliticaNivel(Base):
    """Nivel exigido para ver um tipo de dado, ajustado por uma equipe.

    So existe linha para o tipo que a equipe ajustou; os demais seguem o nivel
    padrao de `configuracoes_regex()`. Vale para os documentos enviados depois
    da alteracao: os ja processados guardam o nivel em `dado_sensivel`.
    """

    __tablename__ = "politica_nivel"
    __table_args__ = (
        UniqueConstraint("team_id", "tipo_entidade", name="uq_politica_nivel_equipe_tipo"),
    )

    politica_id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("equipe.team_id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_entidade = Column(String(50), nullable=False)
    nivel_requerido = Column(Integer, nullable=False)
    atualizado_em = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
