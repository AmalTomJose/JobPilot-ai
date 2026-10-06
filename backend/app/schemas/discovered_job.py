from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict
from app.schemas.job import JobFields, JobWarning

class DiscoveredResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    gmail_url: str | None = None
    source_site: Literal['linkedin', 'naukri', 'indeed', 'other']
    email_message_id: int
    job_url: str | None
    status: Literal['pending', 'dismissed', 'approved']
    job_id: int | None
    draft_data: JobFields
    raw_text: str
    warnings: list[JobWarning]
    parser_version: str
    created_at: datetime

class DiscoveredPage(BaseModel):
    items: list[DiscoveredResponse]
    total: int
    limit: int
    offset: int

class DiscoveryStatus(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['pending', 'dismissed']
