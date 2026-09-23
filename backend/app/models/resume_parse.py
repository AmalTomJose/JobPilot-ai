from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ResumeParse(Base):
    __tablename__ = 'resume_parses'
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name='ck_resume_parses_status'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey('resumes.id', ondelete='CASCADE'), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='pending', nullable=False)
    parser_version: Mapped[str] = mapped_column(String(40), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    draft_data: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB(), 'postgresql'), nullable=True)
    warnings: Mapped[list] = mapped_column(JSON().with_variant(JSONB(), 'postgresql'), default=list, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
