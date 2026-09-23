from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.resume import Resume


class ResumeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, *, user_id: int, file_name: str, file_path: str,
               file_type: str, file_size: int, raw_text: str) -> Resume:
        resume = Resume(user_id=user_id, file_name=file_name, file_path=file_path,
                        file_type=file_type, file_size=file_size, raw_text=raw_text)
        try:
            self.db.add(resume)
            self.db.flush()
            self.db.refresh(resume)
            # Metadata and extracted text are persisted in one transaction.
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return resume

    def get_by_id(self, resume_id: int, user_id: int) -> Resume | None:
        return self.db.scalar(select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id))

    def get_by_user_id(self, user_id: int, *, limit: int = 50, offset: int = 0) -> list[Resume]:
        return list(self.db.scalars(select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc(), Resume.id.desc()).limit(limit).offset(offset)))
