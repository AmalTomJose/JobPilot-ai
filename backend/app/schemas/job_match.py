from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class MatchedSkill(BaseModel):
    job_skill: str
    profile_skill: str


class MatchItem(BaseModel):
    job_id: int
    title: str
    company: str | None
    job_status: Literal['saved', 'archived']
    state: Literal['pending', 'current', 'outdated']
    score: float | None
    matched_skills: list[MatchedSkill]
    missing_skills: list[str]
    reason: str | None
    profile_revision: int | None
    job_revision: int | None
    matcher_version: str | None
    computed_at: datetime | None


class MatchPage(BaseModel):
    items: list[MatchItem]
    total: int
    pending: int
    outdated: int
    limit: int
    offset: int
    profile_ready: bool
    profile_has_skills: bool


class MatchRun(BaseModel):
    processed: int
    scored: int
    insufficient: int
    matcher_version: str
