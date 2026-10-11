"""AI proposals cite profile facts; only explicit human approval enables export."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.profile import ProfileData

Section = Literal['summary', 'skills', 'experience', 'projects', 'education']

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Statement(StrictModel):
    text: str = Field(min_length=1, max_length=1000)
    evidence: list[str] = Field(min_length=1, max_length=12)

class EntrySuggestion(StrictModel):
    source_index: int = Field(ge=0)
    bullets: list[Statement] = Field(max_length=30)

class TailoringProposal(StrictModel):
    summary: Statement | None
    skills: list[str] = Field(max_length=200)
    experience: list[EntrySuggestion] = Field(max_length=50)
    projects: list[EntrySuggestion] = Field(max_length=50)
    section_order: list[Section] = Field(min_length=5, max_length=5)
    changes: list[str] = Field(max_length=20)
    questions: list[str] = Field(max_length=20)

class GenerateTailoring(StrictModel):
    request_id: UUID
    profile_revision: int = Field(ge=1)
    job_revision: int = Field(ge=1)
    consent: Literal[True]

class SaveTailoring(StrictModel):
    expected_revision: int = Field(ge=1)
    data: ProfileData
    section_order: list[Section] = Field(min_length=5, max_length=5)
    approve: bool = False

class TailoringResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    revision: int
    status: str
    profile_revision: int
    job_revision: int
    profile_snapshot: dict
    job_snapshot: dict
    data: ProfileData | None
    proposal: TailoringProposal | None
    section_order: list[Section]
    model: str
    prompt_version: str
    error: str | None
    pdf_filename: str | None = None
    saved_pdf: str | None = None
    stale: bool = False
    created_at: datetime
    approved_at: datetime | None
