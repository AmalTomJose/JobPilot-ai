from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.resume_parse import utc_now


class Profile(Base):
    __tablename__ = 'profiles'
    __table_args__ = (CheckConstraint('revision >= 1', name='ck_profiles_revision'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    source_resume_id: Mapped[int | None] = mapped_column(ForeignKey('resumes.id', ondelete='SET NULL'), nullable=True)
    source_parser_version: Mapped[str] = mapped_column(String(40), nullable=False)
    revision: Mapped[int] = mapped_column(default=1, nullable=False)
    data: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), 'postgresql'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
