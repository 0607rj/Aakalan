"""The public contact page: anyone can send a message (no account needed), a few an hour
from one address (settings `contact_ip_max_per_hour`)."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import DbSession
from app.models import ContactMessage
from app.services import limits

router = APIRouter(tags=["contact"])


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    organisation: str = Field(default="", max_length=300)
    topic: Literal["demo", "question", "partnership", "other"] = "question"
    message: str = Field(min_length=5, max_length=4000)


class ContactOut(BaseModel):
    id: str


@router.post("/contact", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def send_message(body: ContactIn, db: DbSession, request: Request) -> ContactOut:
    try:
        limits.spend_contact(db, request.client.host if request.client else "unknown")
    except limits.LimitError as exc:
        db.commit()
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            exc.message,
            headers={"Retry-After": str(exc.seconds)},
        ) from exc
    row = ContactMessage(
        name=body.name.strip(),
        email=body.email.strip(),
        organisation=body.organisation.strip(),
        topic=body.topic,
        message=body.message.strip(),
    )
    db.add(row)
    db.commit()
    return ContactOut(id=row.id)
