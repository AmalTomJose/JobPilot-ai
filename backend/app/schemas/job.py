"""Contracts for immutable email imports and human-reviewed jobs."""
from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]
WorkMode = Literal['remote', 'hybrid', 'onsite']
JobStatus = Literal['saved', 'archived']


def validate_job_url(value):
    if value is None:
        return None
    try:
        url = urlsplit(value)
        if url.scheme not in {'http', 'https'} or not url.hostname or url.username or url.password or any(char.isspace() or ord(char) < 32 for char in value):
            raise ValueError()
        url.port
        url.hostname.encode('idna')
    except (ValueError, UnicodeError):
        raise ValueError('Application URL must be a complete http:// or https:// address without credentials')
    return value


class JobFields(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: Short | None = None
    company: Short | None = None
    location: Short | None = None
    work_mode: WorkMode | None = None
    employment_type: Short | None = None
    description: Description | None = None
    skills: list[Short] = Field(default_factory=list, max_length=100)
    application_url: Annotated[str, StringConstraints(max_length=2048)] | None = None

    @field_validator('*', mode='before')
    @classmethod
    def blanks(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    _url = field_validator('application_url')(validate_job_url)


class JobCreate(JobFields):
    title: Short
    import_id: int | None = Field(default=None, gt=0)


class JobUpdate(JobFields):
    title: Short
    expected_revision: int = Field(ge=1, strict=True)
    status: JobStatus = 'saved'


class EmailImportRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    raw_text: str = Field(min_length=1, max_length=100000)

    @field_validator('raw_text')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Paste the job email text before extracting')
        return value  # Preserve the original exactly.


class JobWarning(BaseModel):
    code: str
    field: str
    message: str


class JobParseResult(BaseModel):
    draft_data: JobFields
    warnings: list[JobWarning]
    parser_version: str


class DuplicateJob(BaseModel):
    id: int
    title: str
    company: str | None
    reason: str


class JobImportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    raw_text: str
    draft_data: JobFields
    warnings: list[JobWarning]
    parser_version: str
    created_at: datetime
    duplicate: DuplicateJob | None = None


class JobSummary(JobFields):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    source_type: Literal['manual', 'email']
    source_import_id: int | None
    status: JobStatus
    revision: int
    created_at: datetime
    updated_at: datetime


class JobDetail(JobSummary):
    source: JobImportResponse | None = None


class JobPage(BaseModel):
    items: list[JobSummary]
    total: int
    limit: int
    offset: int


class ImportSummary(BaseModel):
    id: int
    title: str | None
    company: str | None
    created_at: datetime


class ImportPage(BaseModel):
    items: list[ImportSummary]
    total: int
    limit: int
    offset: int
