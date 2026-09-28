from sqlalchemy import select, func
from app.models.user import User
from app.models.profile import Profile
from app.models.job import Job
from app.models.job_match import JobMatch


class MatchRepository:
    def __init__(self, db):
        self.db = db

    def lock_owner(self, user_id):
        return self.db.scalar(select(User).where(User.id == user_id).with_for_update(nowait=True))

    def profile(self, user_id):
        return self.db.scalar(select(Profile).where(Profile.user_id == user_id))

    def rows(self, user_id, include_archived=False):
        statement = select(Job, JobMatch).outerjoin(JobMatch, (JobMatch.job_id == Job.id) & (JobMatch.user_id == user_id)).where(Job.user_id == user_id)
        if not include_archived:
            statement = statement.where(Job.status == 'saved')
        return statement

    def count(self, statement):
        return self.db.scalar(select(func.count()).select_from(statement.subquery()))
