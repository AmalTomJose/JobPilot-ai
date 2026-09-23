"""Human-reviewed data. Parser evidence belongs to the source, not the profile."""
from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from email_validator import validate_email, EmailNotValidError
from urllib.parse import urlsplit

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
ListItem = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class ReviewModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    @field_validator('*', mode='before')
    @classmethod
    def empty_strings_are_unknown(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value


def checked_links(values):
    for value in values:
        try:
            parsed = urlsplit(value)
            if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError()
            parsed.port
        except ValueError:
            raise ValueError('Links must be complete http:// or https:// URLs without credentials')
    return values


class ProfileContact(ReviewModel):
    name: ShortText | None = None
    email: ShortText | None = None
    phone: ShortText | None = None
    location: ShortText | None = None
    links: list[ListItem] = Field(default_factory=list, max_length=20)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        if value is not None:
            try:
                return validate_email(value, check_deliverability=False).normalized
            except EmailNotValidError:
                raise ValueError('Enter a valid contact email or leave it empty')
        return value

    _links = field_validator('links')(checked_links)


class ProfileExperience(ReviewModel):
    title: ShortText | None = None
    company: ShortText | None = None
    location: ShortText | None = None
    date_text: ShortText | None = None
    description: list[ListItem] = Field(default_factory=list, max_length=100)


class ProfileEducation(ReviewModel):
    institution: ShortText | None = None
    degree: ShortText | None = None
    field_of_study: ShortText | None = None
    date_text: ShortText | None = None


class ProfileProject(ReviewModel):
    name: ShortText | None = None
    description: list[ListItem] = Field(default_factory=list, max_length=100)
    technologies: list[ShortText] = Field(default_factory=list, max_length=100)
    links: list[ListItem] = Field(default_factory=list, max_length=20)
    _links = field_validator('links')(checked_links)


class ProfileData(ReviewModel):
    contact: ProfileContact = Field(default_factory=ProfileContact)
    summary: LongText | None = None
    skills: list[ShortText] = Field(default_factory=list, max_length=200)
    experience: list[ProfileExperience] = Field(default_factory=list, max_length=50)
    education: list[ProfileEducation] = Field(default_factory=list, max_length=50)
    projects: list[ProfileProject] = Field(default_factory=list, max_length=50)

    @model_validator(mode='after')
    def require_content(self):
        def populated(value):
            if isinstance(value, dict):
                return any(populated(item) for item in value.values())
            if isinstance(value, list):
                return any(populated(item) for item in value)
            return bool(value)
        if not populated(self.model_dump()):
            raise ValueError('Add at least one profile detail before saving')
        return self


class ProfileSave(ReviewModel):
    source_resume_id: int | None = Field(default=None, gt=0)
    expected_revision: int = Field(ge=0, strict=True)
    data: ProfileData


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_resume_id: int | None
    source_parser_version: str
    revision: int
    data: ProfileData
    created_at: datetime
    updated_at: datetime
