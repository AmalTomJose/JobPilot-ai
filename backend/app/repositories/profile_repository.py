from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.profile import Profile
from app.repositories.resume_parse_repository import ResumeParseRepository


class ProfileRepository:
    def __init__(self, db: Session):
        self.db = db
        self.resumes = ResumeParseRepository(db)

    def lock_owner(self, user_id):
        # Serialize even the first save, when no profile row exists yet.
        return self.db.scalar(select(User).where(User.id == user_id).with_for_update(nowait=True))

    def get(self, user_id):
        return self.db.scalar(select(Profile).where(Profile.user_id == user_id))

    def add(self, profile):
        self.db.add(profile)

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
