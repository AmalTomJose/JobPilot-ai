from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads" / "resumes"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int

    @field_validator("UPLOAD_DIR", mode="after")
    @classmethod
    def absolute_upload_dir(cls, value: Path) -> Path:
        return value if value.is_absolute() else BACKEND_DIR / value

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        extra="ignore"
    )


settings = Settings()