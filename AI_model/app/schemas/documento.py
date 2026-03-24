from pydantic import BaseModel, ConfigDict
from sqlalchemy import BIGINT
from datetime import datetime

class DocumentoBase(BaseModel):
    nome_original: str
    extensao: str
    tamanho_bytes: BIGINT
    nivel_segurancao: int
    chave_criptografica: str
    hash_documento: str


class DocumentoCreate(DocumentoBase):
    user_id: int


class DocumentoResponse(DocumentoBase):
    criado_em: datetime
    user_id: int

    model_config = ConfigDict(from_attributes=True)