from sqlalchemy import case, or_
from sqlalchemy.exc import DBAPIError
from app.middlewares.exception_middleware import UserException
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.resume_parse import utc_now
from app.services.skill_matcher import MATCHER_VERSION, match_skills, skill_map


class MatchService:
    def __init__(self, repository):
        self.repository = repository

    def run(self, user_id):
        db = self.repository.db
        try:
            if self.repository.lock_owner(user_id) is None:
                raise UserException(404, 'Account not found')
            profile = self.repository.profile(user_id)
            if profile is None:
                raise UserException(409, 'Confirm your profile before finding matches.')
            processed = scored = 0
            for job, record in db.execute(self.repository.rows(user_id)).all():
                result = match_skills(profile.data.get('skills', []), job.skills)
                if record is None:
                    record = JobMatch(user_id=user_id, job_id=job.id)
                    db.add(record)
                record.profile_id = profile.id
                record.profile_revision = profile.revision
                record.job_revision = job.revision
                record.matcher_version = MATCHER_VERSION
                record.computed_at = utc_now()
                for key, value in result.items():
                    setattr(record, key, value)
                processed += 1
                scored += result['score'] is not None
            db.commit()
            return dict(processed=processed, scored=scored, insufficient=processed-scored, matcher_version=MATCHER_VERSION)
        except DBAPIError as error:
            db.rollback()
            if getattr(error.orig, 'sqlstate', None) == '55P03':
                raise UserException(409, 'Your profile or jobs are being updated. Please try matching again shortly.') from error
            raise
        except Exception:
            db.rollback()
            raise

    def list(self, user_id, include_archived=False, limit=20, offset=0):
        repo = self.repository
        profile = repo.profile(user_id)
        rows = repo.rows(user_id, include_archived)
        stale = or_(JobMatch.profile_id != (profile.id if profile else -1),
                    JobMatch.profile_revision != (profile.revision if profile else -1),
                    JobMatch.job_revision != Job.revision, JobMatch.matcher_version != MATCHER_VERSION)
        # Current scored jobs first, then current unscored, outdated, and pending.
        rank = case((JobMatch.id.is_(None), 3), (stale, 2), (JobMatch.score.is_(None), 1), else_=0)
        records = repo.db.execute(rows.order_by(rank, JobMatch.score.desc().nullslast(), Job.id.desc()).offset(offset).limit(limit)).all()
        items = []
        for job, record in records:
            state = 'pending' if record is None else 'outdated' if (profile is None or record.profile_id != profile.id or record.profile_revision != profile.revision or record.job_revision != job.revision or record.matcher_version != MATCHER_VERSION) else 'current'
            items.append(dict(job_id=job.id, title=job.title, company=job.company, job_status=job.status, state=state,
                              **{key: getattr(record, key) if record else ([] if key in {'matched_skills', 'missing_skills'} else None)
                                 for key in ('score', 'matched_skills', 'missing_skills', 'reason', 'profile_revision', 'job_revision', 'matcher_version', 'computed_at')}))
        return dict(items=items, total=repo.count(rows), pending=repo.count(rows.where(JobMatch.id.is_(None))),
                    outdated=repo.count(rows.where(JobMatch.id.is_not(None), stale)), limit=limit, offset=offset,
                    profile_ready=profile is not None, profile_has_skills=bool(profile and skill_map(profile.data.get('skills', []))))
