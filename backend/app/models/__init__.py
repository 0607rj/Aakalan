"""SQLAlchemy models. Import every model module here so Alembic sees all tables."""

from app.models.base import Base
from app.models.contact import ContactMessage
from app.models.org import Organisation, OrgSettings, Role, User
from app.models.project import (
    Assumption,
    ComponentInstance,
    CostLine,
    Document,
    Estimate,
    Outcome,
    Project,
    QuestionnaireAnswer,
    Requirement,
    Template,
)
from app.models.reference import (
    CatalogComponent,
    ParameterSet,
    RateCard,
    RateItem,
    TaxonomyVersion,
)
from app.models.research import ResearchedComponent
from app.models.review import SecondOpinion

__all__ = [
    "Assumption",
    "Base",
    "CatalogComponent",
    "ComponentInstance",
    "ContactMessage",
    "CostLine",
    "Document",
    "Estimate",
    "OrgSettings",
    "Organisation",
    "Outcome",
    "ParameterSet",
    "Project",
    "QuestionnaireAnswer",
    "RateCard",
    "RateItem",
    "Requirement",
    "ResearchedComponent",
    "Role",
    "SecondOpinion",
    "TaxonomyVersion",
    "Template",
    "User",
]
