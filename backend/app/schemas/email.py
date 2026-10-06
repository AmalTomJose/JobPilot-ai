from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class GmailSelection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    label_id: str = Field(min_length=1, max_length=255)
    import_since: date
    auto_sync: bool = False

    @field_validator('import_since')
    @classmethod
    def past_date(cls, value):
        if value > date.today():
            raise ValueError('Choose today or an earlier import date')
        return value


class GmailStatus(BaseModel):
    configured: bool
    status: str
    mailbox_email: str | None = None
    label_id: str | None = None
    label_name: str | None = None
    import_since: datetime | None = None
    auto_sync: bool = False
    next_sync_at: datetime | None = None
    last_sync_at: datetime | None = None
    last_error: str | None = None
    has_more: bool = False


class GmailLabel(BaseModel):
    id: str
    name: str


class SyncRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    imported: int
    skipped: int
    needs_review: int
    error: str | None


class OpeningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str | None
    job_url: str


class EmailSummary(BaseModel):
    gmail_url: str | None = None
    model_config = ConfigDict(from_attributes=True)
    id: int
    subject: str
    sender: str
    received_at: datetime | None
    import_id: int | None
    status: str
    warning: str | None
    openings: list[OpeningResponse] = Field(default_factory=list)


class EmailPage(BaseModel):
    items: list[EmailSummary]
    total: int
    limit: int
    offset: int
