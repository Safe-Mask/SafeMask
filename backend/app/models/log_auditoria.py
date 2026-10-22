from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class LogAuditoria(Base):
    """Trilha de auditoria: uma linha por operacao sensivel.

    Guarda so identificadores, a acao, o resultado e o instante; nunca o
    conteudo do documento nem o dado pessoal detectado.

    As FKs de contexto (`doc_id`, `team_id`, `cargo_id`, `alvo_user_id`) usam
    ON DELETE SET NULL: apagar um documento ou uma equipe nao pode apagar o
    rastro de quem os acessou. `cargo_id` e o cargo de quem agiu no momento da
    acao; `alvo_user_id` so e preenchido quando a acao recai sobre outra pessoa
    (adicionar, remover membro, alterar cargo). Bancos criados antes destas
    colunas as recebem em `garantir_schema_auditoria()`.
    """

    __tablename__ = "log_auditoria"

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuario.user_id", ondelete="CASCADE"), nullable=False, index=True)
    acao = Column(String(100), nullable=False)
    ip_origem = Column(String(45), nullable=False)
    data_hora = Column(TIMESTAMP, server_default=func.now())
    doc_id = Column(Integer, ForeignKey("documentos.doc_id", ondelete="SET NULL"), nullable=True)
    team_id = Column(Integer, ForeignKey("equipe.team_id", ondelete="SET NULL"), nullable=True)
    cargo_id = Column(Integer, ForeignKey("cargo.cargo_id", ondelete="SET NULL"), nullable=True)
    alvo_user_id = Column(Integer, ForeignKey("usuario.user_id", ondelete="SET NULL"), nullable=True)
    resultado = Column(String(20), nullable=False, default="sucesso", server_default="sucesso")

    usuario = relationship("Usuario", back_populates="logs_auditoria", foreign_keys=[user_id])
