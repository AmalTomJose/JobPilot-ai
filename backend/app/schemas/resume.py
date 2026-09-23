from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ResumeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    file_type: str
    file_size: int
    created_at: datetime


class ResumeResponse(ResumeSummary):
    raw_text: str | None
