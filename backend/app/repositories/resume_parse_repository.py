from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.resume import Resume
from app.models.resume_parse import ResumeParse


class ResumeParseRepository:
    def __init__(self, db: Session):
        self.db = db

    def owned_resume(self, resume_id: int, user_id: int, *, lock=False):
        statement = select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        if lock:
            # All parse requests lock the parent, even before a draft row exists.
            statement = statement.with_for_update(nowait=True)
        return self.db.scalar(statement)

    def get(self, resume_id: int):
        return self.db.scalar(select(ResumeParse).where(ResumeParse.resume_id == resume_id))

    def add(self, record: ResumeParse):
        self.db.add(record)

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
