"""Shared org-scoped query helpers. Every tenant query must go through these (rule 8)."""

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session


def scoped[T](model: type[T], org_id: str) -> Select[T]:
    """`SELECT model WHERE model.org_id = org_id`. Raises if the model is not a tenant table."""
    column: Any = getattr(model, "org_id", None)
    if column is None:
        raise TypeError(f"{model.__name__} is not a tenant table (no org_id)")
    return select(model).where(column == org_id)


def get_owned[T](session: Session, model: type[T], obj_id: str, org_id: str) -> T:
    """Fetch one row by id within the caller's organisation, else 404 (never 403, no leak)."""
    id_column: Any = getattr(model, "id")  # noqa: B009
    obj = session.scalars(scoped(model, org_id).where(id_column == obj_id)).first()
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")
    return obj
