"""API schemas for projects, requirements, questionnaire and component instances."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.engine.inputs import SourceRef
from app.services.engine.reference import Complexity, Size

BuyerType = Literal["govt", "psu", "private"]
RequirementCategory = Literal[
    "functional", "NFR", "integration", "compliance", "commercial", "O&M", "manpower"
]
RequirementStatus = Literal["extracted", "confirmed", "rejected", "edited"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    buyer_type: BuyerType = "psu"
    domain: str = Field(default="general", max_length=100)
    description: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    buyer_type: BuyerType | None = None
    domain: str | None = None
    description: str | None = None


class ProjectOut(ORM):
    id: str
    name: str
    buyer_type: str
    domain: str
    mode: str
    status: str
    description: str
    created_at: datetime


class RequirementCreate(BaseModel):
    code: str | None = Field(default=None, max_length=30)
    text: str = Field(min_length=1)
    category: RequirementCategory = "functional"
    clarity_score: int = Field(default=3, ge=1, le=5)
    source_refs: list[SourceRef] = Field(min_length=1)


class RequirementUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=1)
    category: RequirementCategory | None = None
    clarity_score: int | None = Field(default=None, ge=1, le=5)
    source_refs: list[SourceRef] | None = None
    status: Literal["confirmed", "rejected"] | None = None


class RequirementOut(ORM):
    id: str
    project_id: str
    code: str
    text: str = Field(validation_alias="text_normalised")
    category: str
    clarity_score: int
    status: str
    source_refs: list[SourceRef]
    confirmed_at: datetime | None


class ConfirmRequest(BaseModel):
    requirement_ids: list[str] | None = None  # None = all extracted / edited requirements


class AnswerIn(BaseModel):
    key: str
    value: Any = None
    requirement_ids: list[str] = []


class QuestionnairePut(BaseModel):
    answers: list[AnswerIn]


class QuestionnaireField(BaseModel):
    key: str
    title: str
    schema_: dict[str, Any] = Field(serialization_alias="schema")
    default: Any
    value: Any
    source: Literal["user", "default"]
    requirement_ids: list[str]
    restricted: bool = False  # finance/admin only


class QuestionnaireOut(BaseModel):
    parameter_set_version: str
    fields: list[QuestionnaireField]


class ComponentIn(BaseModel):
    catalog_key: str
    label: str | None = None
    size: Size
    complexity: Complexity = Complexity.MEDIUM
    quantity: int = Field(default=1, ge=1)
    requirement_ids: list[str] = []


class ComponentsPut(BaseModel):
    components: list[ComponentIn]


class ComponentOut(ORM):
    id: str
    catalog_key: str
    label: str | None
    size: str
    complexity: str
    quantity: int
    requirement_ids: list[str]
    status: str
    confirmed_at: datetime | None


class CatalogComponentOut(BaseModel):
    key: str
    name: str
    category: str
    bucket: str
    description: str
    base_effort_pd: dict[str, str]
    applicable_drivers: list[str]
    tags: list[str]
    licensable: bool
    source: str


class CatalogOut(BaseModel):
    version: str
    components: list[CatalogComponentOut]
