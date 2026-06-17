from pydantic import BaseModel, EmailStr


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr