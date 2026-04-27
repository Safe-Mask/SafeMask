from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class EquipeBase(BaseModel):
    nome: str
    descricao: str | None = None


class EquipeCreate(EquipeBase):
    membros_ids: List[int] = Field(default_factory=list)


class EquipeMemberResponse(BaseModel):
    user_team_id: int
    user_id: int
    nome: str
    email: str
    cargo_nome: str
    cargo_nivel: int
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class EquipeDetailResponse(BaseModel):
    team_id: int
    nome: str
    descricao: str | None = None
    criado_em: datetime
    membros: int
    documentos: int
    membros_lista: List[EquipeMemberResponse]

    model_config = ConfigDict(from_attributes=True)