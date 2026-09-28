from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.resume_parse import utc_now


class JobImport(Base):
    __tablename__ = 'job_imports'
    __table_args__ = (UniqueConstraint('user_id', 'source_hash', name='uq_job_imports_user_hash'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(40), nullable=False)
    draft_data: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), 'postgresql'), nullable=False)
    warnings: Mapped[list] = mapped_column(JSON().with_variant(JSONB(), 'postgresql'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class Job(Base):
    __tablename__ = 'jobs'
    __table_args__ = (
        UniqueConstraint('user_id', 'url_hash', name='uq_jobs_user_url'),
        UniqueConstraint('source_import_id', name='uq_jobs_import'),
        CheckConstraint("status IN ('saved', 'archived')", name='ck_jobs_status'),
        CheckConstraint("source_type IN ('manual', 'email')", name='ck_jobs_source'),
        CheckConstraint("work_mode IS NULL OR work_mode IN ('remote', 'hybrid', 'onsite')", name='ck_jobs_work_mode'),
        CheckConstraint('revision >= 1', name='ck_jobs_revision'),
        Index('ix_jobs_user_created', 'user_id', 'created_at', 'id'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    source_import_id: Mapped[int | None] = mapped_column(ForeignKey('job_imports.id', ondelete='SET NULL'), nullable=True)
    source_type: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_mode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list] = mapped_column(JSON().with_variant(JSONB(), 'postgresql'), nullable=False)
    application_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default='saved', nullable=False)
    revision: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
