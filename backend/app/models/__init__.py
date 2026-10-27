"""SQLAlchemy models. Import every model module here so Alembic sees all tables."""

from app.models.base import Base
from app.models.contact import ContactMessage
from app.models.org import OneTimeCode, Organisation, OrgSettings, Role, User
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
from app.models.reading import DescriptionReading
from app.models.reference import (
    CatalogComponent,
    ParameterSet,
    RateCard,
    RateItem,
    TaxonomyVersion,
)
from app.models.research import ResearchedComponent, SharedResearchedComponent
from app.models.review import SecondOpinion

__all__ = [
    "Assumption",
    "Base",
    "CatalogComponent",
    "ComponentInstance",
    "ContactMessage",
    "CostLine",
    "DescriptionReading",
    "Document",
    "Estimate",
    "OneTimeCode",
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
    "SharedResearchedComponent",
    "TaxonomyVersion",
    "Template",
    "User",
]
