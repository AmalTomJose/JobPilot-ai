from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.resume_parse import utc_now


class JobMatch(Base):
    __tablename__ = 'job_matches'
    __table_args__ = (
        UniqueConstraint('job_id', name='uq_job_matches_job'),
        CheckConstraint('score IS NULL OR (score >= 0 AND score <= 100)', name='ck_job_matches_score'),
        CheckConstraint('profile_revision >= 1 AND job_revision >= 1', name='ck_job_matches_revisions'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)
    profile_revision: Mapped[int] = mapped_column(nullable=False)
    job_revision: Mapped[int] = mapped_column(nullable=False)
    matcher_version: Mapped[str] = mapped_column(String(40), nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    matched_skills: Mapped[list] = mapped_column(JSON().with_variant(JSONB(), 'postgresql'), nullable=False)
    missing_skills: Mapped[list] = mapped_column(JSON().with_variant(JSONB(), 'postgresql'), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
