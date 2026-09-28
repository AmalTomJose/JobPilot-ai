from sqlalchemy import select, func, or_, exists
from sqlalchemy.orm import Session
from app.models.job import Job, JobImport
from app.models.user import User


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def lock_owner(self, user_id):
        return self.db.scalar(select(User).where(User.id == user_id).with_for_update(nowait=True))

    def get(self, job_id, user_id):
        return self.db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user_id))

    def get_import(self, import_id, user_id):
        return self.db.scalar(select(JobImport).where(JobImport.id == import_id, JobImport.user_id == user_id))

    def import_by_hash(self, user_id, fingerprint):
        return self.db.scalar(select(JobImport).where(JobImport.user_id == user_id, JobImport.source_hash == fingerprint))

    def duplicate(self, user_id, url_hash=None, import_id=None, exclude_id=None):
        conditions = []
        if url_hash:
            conditions.append(Job.url_hash == url_hash)
        if import_id:
            conditions.append(Job.source_import_id == import_id)
        if not conditions:
            return None
        query = select(Job).where(Job.user_id == user_id, or_(*conditions))
        if exclude_id is not None:
            query = query.where(Job.id != exclude_id)
        return self.db.scalar(query.order_by(Job.id))

    def list(self, user_id, q='', status=None, source=None, work_mode=None, limit=20, offset=0):
        conditions = [Job.user_id == user_id]
        if q:
            # Escape LIKE wildcards: user input is a literal search, not a pattern.
            conditions.append(or_(*(func.lower(column).contains(q.lower(), autoescape=True) for column in (Job.title, Job.company, Job.location, Job.description))))
        for column, value in ((Job.status, status), (Job.source_type, source), (Job.work_mode, work_mode)):
            if value:
                conditions.append(column == value)
        total = self.db.scalar(select(func.count()).select_from(Job).where(*conditions))
        items = self.db.scalars(select(Job).where(*conditions).order_by(Job.created_at.desc(), Job.id.desc()).offset(offset).limit(limit)).all()
        return dict(items=items, total=total, limit=limit, offset=offset)

    def imports(self, user_id, limit=20, offset=0):
        conditions = [JobImport.user_id == user_id, ~exists(select(Job.id).where(Job.source_import_id == JobImport.id))]
        total = self.db.scalar(select(func.count()).select_from(JobImport).where(*conditions))
        rows = self.db.scalars(select(JobImport).where(*conditions).order_by(JobImport.created_at.desc(), JobImport.id.desc()).offset(offset).limit(limit)).all()
        return dict(items=[dict(id=row.id, title=row.draft_data.get('title'), company=row.draft_data.get('company'), created_at=row.created_at) for row in rows], total=total, limit=limit, offset=offset)

    def add(self, row):
        self.db.add(row)

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
