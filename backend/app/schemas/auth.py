from pydantic import BaseModel, EmailStr, Field


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class ResetSenhaRequest(BaseModel):
    """Payload do reset de senha.

    `dict` sem tipo aceitava qualquer coisa: `senha` faltando virava `None` e
    chegava ao bcrypt; `senha` numerica quebrava o backend com 500. Aqui os
    dois viram 422, na borda.
    """

    token: str = Field(min_length=1)
    senha: str = Field(min_length=8, max_length=128)
