from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class LogAuditoria(Base):
    __tablename__ = "log_auditoria"

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuario.user_id", ondelete="CASCADE"), nullable=False, index=True)
    acao = Column(String(100), nullable=False)
    ip_origem = Column(String(45), nullable=False)
    data_hora = Column(TIMESTAMP, server_default=func.now())

    usuario = relationship("Usuario", back_populates="logs_auditoria")
