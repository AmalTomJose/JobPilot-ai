"""The parser contract. Unknown values stay None; repeated fields use lists."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ContactDraft(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[str] = Field(default_factory=list)


class ExperienceDraft(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    date_text: str | None = None
    description: list[str] = Field(default_factory=list)
    source_text: str


class EducationDraft(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    date_text: str | None = None
    source_text: str


class ProjectDraft(BaseModel):
    name: str | None = None
    description: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    source_text: str


class ResumeDraft(BaseModel):
    contact: ContactDraft = Field(default_factory=ContactDraft)
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceDraft] = Field(default_factory=list)
    education: list[EducationDraft] = Field(default_factory=list)
    projects: list[ProjectDraft] = Field(default_factory=list)
    # Preserve blocks whose section or entry structure is not supported yet.
    unclassified_text: str | None = None


class ParseWarning(BaseModel):
    code: str
    section: str
    message: str


class ParseResult(BaseModel):
    draft: ResumeDraft
    warnings: list[ParseWarning] = Field(default_factory=list)
    parser_version: str


class ResumeParseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    resume_id: int
    status: Literal['pending', 'processing', 'completed', 'failed']
    parser_version: str
    draft_data: ResumeDraft | None
    warnings: list[ParseWarning]
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
