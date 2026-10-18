"""Templates: saved starting points for new quick estimates (the form answers of an earlier
estimate). Org-scoped like every tenant table."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, EditorUser
from app.core.tenancy import get_owned, scoped
from app.models import Project, Template

router = APIRouter(tags=["templates"])


class TemplateIn(BaseModel):
    project_id: str  # the estimate's project whose form answers become the template
    name: str = Field(min_length=1, max_length=300)


class TemplateOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    features: list[str]  # ready-made feature keys, for a short preview
    extra_features: int  # how many features were added by hand
    request: dict[str, Any]  # the form answers to pre-fill a new estimate


def _out(t: Template) -> TemplateOut:
    return TemplateOut(
        id=t.id,
        name=t.name,
        created_at=t.created_at,
        features=list(t.request.get("features", [])),
        extra_features=len(t.request.get("custom_features", [])),
        request=t.request,
    )


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(db: DbSession, user: CurrentUser) -> list[TemplateOut]:
    rows = db.scalars(scoped(Template, user.org_id).order_by(Template.created_at.desc()))
    return [_out(t) for t in rows]


@router.post("/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(body: TemplateIn, db: DbSession, user: EditorUser) -> TemplateOut:
    project = get_owned(db, Project, body.project_id, user.org_id)
    if not project.quick_request:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only estimates made with the simple form can be saved as templates.",
        )
    template = Template(
        org_id=user.org_id,
        name=body.name.strip(),
        request={**project.quick_request, "name": body.name.strip()},
        source_project_id=project.id,
        created_by=user.id,
    )
    db.add(template)
    db.commit()
    return _out(template)


@router.get("/templates/{template_id}", response_model=TemplateOut)
def get_template(template_id: str, db: DbSession, user: CurrentUser) -> TemplateOut:
    return _out(get_owned(db, Template, template_id, user.org_id))


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: str, db: DbSession, user: EditorUser) -> Response:
    db.delete(get_owned(db, Template, template_id, user.org_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
