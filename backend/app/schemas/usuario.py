
from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Sem `min_length`, `senha_hash: str` aceitava "" e o login com senha vazia
# funcionava. 8 e o piso; `cadastro` e `reset_senha` seguem a mesma regra.
SENHA_MIN = 8
SENHA_MAX = 128


class UsuarioBase(BaseModel):
    email: EmailStr


class UsuarioLogin(UsuarioBase):
    senha_hash: str = Field(min_length=1, max_length=SENHA_MAX)


class UsuarioCreate(UsuarioBase):
    nome: str = Field(min_length=1, max_length=120)
    senha_hash: str = Field(min_length=SENHA_MIN, max_length=SENHA_MAX)

    model_config = ConfigDict(from_attributes=True)
