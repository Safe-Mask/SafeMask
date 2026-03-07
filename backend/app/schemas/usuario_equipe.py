from pydantic import BaseModel, ConfigDict
from datetime import datetime

class UsuarioEquipeBase(BaseModel):
    user_id: int
    team_id: int
    cargo: str

class UsuarioEquipeCreate(UsuarioEquipeBase):
    model_config = ConfigDict(from_attributes=True)

class UsuarioEquipeResponse(UsuarioEquipeBase):
    user_team_id: int
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)