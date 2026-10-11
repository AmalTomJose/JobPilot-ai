from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.email import JSON_DATA
from app.models.resume_parse import utc_now

class TailoredResume(Base):
    __tablename__ = 'tailored_resumes'
    __table_args__ = (
        UniqueConstraint('user_id', 'request_id', name='uq_tailoring_request'),
        CheckConstraint("status IN ('generating','draft','approved','failed')", name='ck_tailoring_status'),
        CheckConstraint('revision >= 1 AND profile_revision >= 1 AND job_revision >= 1', name='ck_tailoring_revisions'),
        Index('ix_tailoring_owner_job', 'user_id', 'job_id', 'id'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    job_id: Mapped[int] = mapped_column(ForeignKey('jobs.id', ondelete='CASCADE'))
    request_id: Mapped[str] = mapped_column(String(36))
    profile_revision: Mapped[int]
    job_revision: Mapped[int]
    revision: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(16), default='generating')
    profile_snapshot: Mapped[dict] = mapped_column(JSON_DATA)
    job_snapshot: Mapped[dict] = mapped_column(JSON_DATA)
    data: Mapped[dict | None] = mapped_column(JSON_DATA, nullable=True)
    proposal: Mapped[dict | None] = mapped_column(JSON_DATA, nullable=True)
    section_order: Mapped[list] = mapped_column(JSON_DATA)
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(40))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
