"""Mailbox credentials stay encrypted; messages and runs are owner-scoped."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, JSON, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.resume_parse import utc_now

JSON_DATA = JSON().with_variant(JSONB(), 'postgresql')


class EmailConnection(Base):
    __tablename__ = 'email_connections'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    mailbox_email: Mapped[str | None] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(30), default='disconnected')
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text)
    state_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    browser_hash: Mapped[str | None] = mapped_column(String(64))
    state_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    verifier_encrypted: Mapped[str | None] = mapped_column(Text)
    label_id: Mapped[str | None] = mapped_column(String(255))
    label_name: Mapped[str | None] = mapped_column(String(255))
    import_since: Mapped[datetime | None] = mapped_column(DateTime)
    auto_sync: Mapped[bool] = mapped_column(default=False)
    next_sync_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(String(500))
    failure_count: Mapped[int] = mapped_column(default=0)
    scan_before: Mapped[int | None] = mapped_column()
    page_token: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class EmailMessage(Base):
    __tablename__ = 'email_messages'
    __table_args__ = (
        UniqueConstraint('user_id', 'mailbox_email', 'provider_message_id', name='uq_email_message_owner_mailbox'),
        Index('ix_email_messages_owner_id', 'user_id', 'id'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    mailbox_email: Mapped[str] = mapped_column(String(320))
    provider_message_id: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(Text)
    sender: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime | None] = mapped_column(DateTime)
    payload_data: Mapped[dict] = mapped_column(JSON_DATA)
    raw_text: Mapped[str | None] = mapped_column(Text)
    import_id: Mapped[int | None] = mapped_column(ForeignKey('job_imports.id', ondelete='SET NULL'))
    status: Mapped[str] = mapped_column(String(30))
    warning: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


    @property
    def gmail_url(self):
        from app.services.gmail_links import original_email_url
        return original_email_url(self)


class EmailSyncRun(Base):
    __tablename__ = 'email_sync_runs'
    __table_args__ = (Index('ix_email_sync_runs_owner_id', 'user_id', 'id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30), default='running')
    imported: Mapped[int] = mapped_column(default=0)
    skipped: Mapped[int] = mapped_column(default=0)
    needs_review: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(String(500))
