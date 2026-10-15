"""Write reference seed data (and an optional demo project) into the database. Idempotent.

Existing versions are never modified (rule 4): if a seed file changes but keeps its version,
the stored version wins and a warning is returned. Bump the version to publish new values.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CatalogComponent,
    ComponentInstance,
    Organisation,
    ParameterSet,
    Project,
    QuestionnaireAnswer,
    RateCard,
    RateItem,
    Requirement,
    TaxonomyVersion,
    User,
)
from app.services.engine import reference as ref
from app.services.seeding.golden import golden_input
from app.services.seeding.reference import ReferenceData


def seed_reference(session: Session, data: ReferenceData) -> list[str]:
    warnings: list[str] = []
    tax = session.scalars(
        select(TaxonomyVersion).where(TaxonomyVersion.version == data.taxonomy.version)
    ).first()
    if tax is None:
        session.add(
            TaxonomyVersion(
                version=data.taxonomy.version,
                source=data.taxonomy.source,
                data=data.taxonomy.model_dump(mode="json"),
            )
        )
    elif tax.data != data.taxonomy.model_dump(mode="json"):
        warnings.append(f"taxonomy {tax.version} differs from seed; stored version kept")

    existing = {
        (c.key, c.version): c
        for c in session.scalars(
            select(CatalogComponent).where(CatalogComponent.version == data.catalog.version)
        )
    }
    for comp in data.catalog.components:
        row = existing.get((comp.key, data.catalog.version))
        spec = comp.model_dump(mode="json")
        if row is None:
            session.add(
                CatalogComponent(
                    key=comp.key,
                    version=data.catalog.version,
                    name=comp.name,
                    category=comp.category,
                    bucket=comp.bucket,
                    description=comp.description,
                    source=comp.source,
                    spec=spec,
                )
            )
        elif row.spec != spec:
            warnings.append(f"catalog {comp.key}@{data.catalog.version} differs; stored kept")

    for card in data.rate_cards:
        row_card = session.scalars(select(RateCard).where(RateCard.version == card.version)).first()
        if row_card is None:
            add_rate_card(session, card)
        elif rate_card_model(row_card) != card:
            warnings.append(f"rate card {card.version} differs from seed; stored version kept")

    for params in data.parameter_sets:
        row_ps = session.scalars(
            select(ParameterSet).where(ParameterSet.version == params.version)
        ).first()
        if row_ps is None:
            session.add(
                ParameterSet(
                    version=params.version,
                    effective_date=params.effective_date,
                    status=params.status,
                    data=params.model_dump(mode="json"),
                )
            )
        elif row_ps.data != params.model_dump(mode="json"):
            warnings.append(f"parameter set {params.version} differs; stored version kept")
    session.flush()
    return warnings


def add_rate_card(session: Session, card: ref.RateCard) -> RateCard:
    row = RateCard(
        version=card.version,
        effective_date=card.effective_date,
        status=card.status,
        source=card.source,
        items=[
            RateItem(
                key=i.key,
                kind=i.kind.value,
                unit=i.unit,
                amount=i.amount,
                currency=i.currency,
                region=i.region,
                source=i.source,
                source_url=i.source_url,
            )
            for i in card.items
        ],
    )
    session.add(row)
    session.flush()
    return row


def rate_card_model(row: RateCard) -> ref.RateCard:
    return ref.RateCard(
        version=row.version,
        effective_date=row.effective_date,
        status=row.status,  # type: ignore[arg-type]
        source=row.source,
        items=[
            ref.RateItem(
                key=i.key,
                kind=ref.RateKind(i.kind),
                unit=i.unit,
                amount=i.amount,
                currency=i.currency,
                region=i.region,
                source=i.source,
                source_url=i.source_url,
            )
            for i in row.items
        ],
    )


DEMO_PROJECT_NAME = "AI chatbot + online empanelment portal (PSU) — demo"


def seed_demo_project(session: Session, org: Organisation, data: ReferenceData) -> Project | None:
    """The medium golden example as a ready-to-price demo project (requirements and components
    already confirmed by the demo estimator)."""
    exists = session.scalars(
        select(Project).where(Project.org_id == org.id, Project.name == DEMO_PROJECT_NAME)
    ).first()
    if exists is not None:
        return None
    user = session.scalars(
        select(User).where(User.org_id == org.id, User.email == "estimator@aakalan.local")
    ).first()
    user_id = user.id if user else None
    now = datetime.now(UTC)
    inp = golden_input("medium", data)
    project = Project(
        org_id=org.id,
        name=DEMO_PROJECT_NAME,
        buyer_type=inp.project.buyer_type,
        domain=inp.project.domain,
        description="Seeded from the medium golden estimate. Every number is a placeholder.",
        created_by=user_id,
    )
    session.add(project)
    session.flush()
    req_ids: dict[str, str] = {}
    for r in inp.requirements:
        row = Requirement(
            org_id=org.id,
            project_id=project.id,
            code=r.code,
            text_normalised=r.text,
            category=r.category,
            clarity_score=r.clarity_score,
            status="confirmed",
            source_refs=[s.model_dump(mode="json") for s in r.source_refs],
            confirmed_by=user_id,
            confirmed_at=now,
        )
        session.add(row)
        session.flush()
        req_ids[r.id] = row.id
    for c in inp.components:
        session.add(
            ComponentInstance(
                org_id=org.id,
                project_id=project.id,
                catalog_key=c.catalog_key,
                label=c.label,
                size=c.size.value,
                complexity=c.complexity.value,
                quantity=c.quantity,
                driver_values={},
                requirement_ids=[req_ids[x] for x in c.requirement_ids],
                status="confirmed",
                confirmed_by=user_id,
                confirmed_at=now,
            )
        )
    for a in inp.answers:
        session.add(
            QuestionnaireAnswer(
                org_id=org.id,
                project_id=project.id,
                key=a.key,
                value=a.value,
                source="user",
                requirement_ids=[req_ids[x] for x in a.requirement_ids],
            )
        )
    session.flush()
    return project
