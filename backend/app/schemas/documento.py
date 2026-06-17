from pydantic import BaseModel, ConfigDict
from datetime import datetime

class DocumentoBase(BaseModel):
    nome_original: str
    extensao: str
    tamanho_bytes: int
    nivel_seguranca: int
    chave_criptografica: str
    hash_documento: str
    caminho_storage: str
    status_processamento: str
    ativo: bool = True


class DocumentoCreate(DocumentoBase):
    user_team_id: int


class DocumentoResponse(DocumentoBase):
    doc_id: int
    criado_em: datetime
    user_team_id: int

    model_config = ConfigDict(from_attributes=True)