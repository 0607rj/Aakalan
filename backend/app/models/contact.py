"""Messages sent from the public contact page. Not tenant data: the sender has no account."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTimestampMixin


class ContactMessage(IdTimestampMixin, Base):
    __tablename__ = "contact_messages"

    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320))
    organisation: Mapped[str] = mapped_column(String(300), default="")
    topic: Mapped[str] = mapped_column(String(40))  # demo / question / partnership / other
    message: Mapped[str] = mapped_column(Text)
