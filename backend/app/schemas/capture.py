"""Browser text is untrusted input. Previewing never writes a database row."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.job import JobFields, JobParseResult, validate_job_url


class CaptureInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(default='', max_length=255)
    company: str = Field(default='', max_length=255)
    description: str = Field(min_length=40, max_length=20000)
    url: str = Field(max_length=2048)

    _url = field_validator('url')(validate_job_url)


class CapturePreview(JobParseResult):
    raw_text: str


class CaptureDraft(BaseModel):
    model_config = ConfigDict(extra='forbid')
    capture: CaptureInput
    draft_data: JobFields
