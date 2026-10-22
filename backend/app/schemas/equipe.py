from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EquipeBase(BaseModel):
    nome: str
    descricao: str | None = None


class EquipeCreate(EquipeBase):
    membros_ids: list[int] = Field(default_factory=list)


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
    membros_lista: list[EquipeMemberResponse]

    model_config = ConfigDict(from_attributes=True)


class EquipeMembroAdd(BaseModel):
    """Corpo de POST /equipes/{team_id}/membros: a pessoa pelo e-mail."""

    email: EmailStr


class EquipeMembroCargo(BaseModel):
    """Corpo de PATCH /equipes/{team_id}/membros/{user_id}: o cargo pelo nome."""

    cargo: str = Field(min_length=1, max_length=50)


class PoliticaNiveisUpdate(BaseModel):
    """Corpo de PUT /equipes/{team_id}/politica-niveis: tipo -> nivel (1 a 3).

    Ex.: {"niveis": {"TELEFONE": 3}}. So os tipos informados mudam.
    """

    niveis: dict[str, int]
