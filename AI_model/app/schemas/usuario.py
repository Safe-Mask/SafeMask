from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime

class UsuarioBase(BaseModel):
    email: EmailStr


class UsuarioLogin(UsuarioBase):
    senha_hash: str


class UsuarioCreate(UsuarioBase):
    nome: str
    senha_hash: str

    model_config = ConfigDict(from_attributes=True)
