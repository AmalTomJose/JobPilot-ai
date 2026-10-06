"""Unapproved opportunities, kept separate from user-saved jobs."""
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, DateTime, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.email import JSON_DATA, EmailMessage
from app.models.resume_parse import utc_now

class DiscoveredJob(Base):
    __tablename__ = 'discovered_jobs'
    __table_args__ = (
        UniqueConstraint('user_id', 'identity_hash', name='uq_discovered_owner_identity'),
        CheckConstraint("status IN ('pending', 'dismissed', 'approved')", name='ck_discovered_status'),
        CheckConstraint("source_site IN ('linkedin', 'naukri', 'indeed', 'other')", name='ck_discovered_site'),
        Index('ix_discovered_owner_site_status', 'user_id', 'source_site', 'status', 'id'),
        Index('ix_discovered_owner_status', 'user_id', 'status', 'id'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    email_message_id: Mapped[int] = mapped_column(ForeignKey('email_messages.id', ondelete='CASCADE'))
    identity_hash: Mapped[str] = mapped_column(String(64))
    source_site: Mapped[str] = mapped_column(String(16), default='other', server_default='other')
    job_url: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(16), default='pending')
    job_id: Mapped[int | None] = mapped_column(ForeignKey('jobs.id', ondelete='SET NULL'))
    draft_data: Mapped[dict] = mapped_column(JSON_DATA)
    raw_text: Mapped[str] = mapped_column(Text)
    warnings: Mapped[list] = mapped_column(JSON_DATA)
    parser_version: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    source_email: Mapped[EmailMessage] = relationship(lazy='selectin', viewonly=True)

    @property
    def gmail_url(self):
        source = self.source_email
        return source.gmail_url if source and source.user_id == self.user_id else None
