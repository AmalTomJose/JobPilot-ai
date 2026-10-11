"""Separate versions preserve source snapshots and require explicit approval."""
from copy import deepcopy
from datetime import timedelta
import re
from sqlalchemy import select, func
from app.core.config import settings
from app.models.profile import Profile
from app.models.tailored_resume import TailoredResume
from app.models.resume_parse import utc_now
from app.repositories.job_repository import JobRepository
from app.services.job_service import JobService
from app.services import tailoring_ai
from app.services.tailoring_storage import store_approved_pdf, approval_path, resume_filename
from app.schemas.profile import ProfileData
from app.schemas.tailoring import TailoringResponse
from app.middlewares.exception_middleware import UserException

SECTIONS = ['summary','skills','experience','projects','education']


def facts_for(profile):
    """Stable IDs within a frozen source snapshot; contact details are excluded."""
    facts = {}
    def walk(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                if key not in {'contact', 'links'}:
                    walk(child, f'{path}.{key}' if path else key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f'{path}.{index}')
        elif value:
            facts[path] = str(value)
    walk(profile, '')
    return facts


def validate_order(order):
    if len(order) != 5 or set(order) != set(SECTIONS):
        raise UserException(422, 'Include each resume section exactly once.')


def assemble(profile, proposal):
    """AI cannot change identity fields or add a skill/entry absent from the profile."""
    facts = facts_for(profile)
    def statement(item, prefix=None):
        if any(key not in facts or prefix and not key.startswith(prefix) for key in item.evidence):
            raise UserException(502, 'AI cited unsupported profile evidence. Please try a new version.')
        evidence = ' '.join(facts[key] for key in item.evidence)
        # Numeric claims must appear in the cited facts. Semantic truth still needs review.
        if set(re.findall(r'\d+(?:[.,]\d+)*(?:%|\+)?', item.text)) - set(re.findall(r'\d+(?:[.,]\d+)*(?:%|\+)?', evidence)):
            raise UserException(502, 'AI introduced an unsupported number. Please try a new version.')
        return item.text
    validate_order(proposal.section_order)
    if len(proposal.skills) != len(set(proposal.skills)) or any(skill not in profile['skills'] for skill in proposal.skills):
        raise UserException(502, 'AI suggested a skill absent from your confirmed profile. Please try a new version.')
    data = deepcopy(profile)
    data['summary'] = statement(proposal.summary) if proposal.summary else None
    data['skills'] = proposal.skills
    for section in ('experience','projects'):
        selected = getattr(proposal, section)
        indexes = [entry.source_index for entry in selected]
        if len(indexes) != len(set(indexes)) or any(index >= len(profile[section]) for index in indexes):
            raise UserException(502, 'AI selected an invalid profile entry. Please try a new version.')
        if set(indexes) != set(range(len(profile[section]))):
            raise UserException(502, 'AI omitted an experience or project. Please generate a new version; every entry must be included.')
        data[section] = []
        for entry in selected:
            original = deepcopy(profile[section][entry.source_index])
            if original.get('description') and not entry.bullets:
                raise UserException(502, 'AI removed an entry description. Please generate a new version.')
            original['description'] = [statement(bullet, f'{section}.{entry.source_index}.') for bullet in entry.bullets]
            data[section].append(original)
    return ProfileData.model_validate(data).model_dump(mode='json')


class TailoringService:
    def __init__(self, db):
        self.db = db
        self.repo = JobRepository(db)

    def source(self, user_id, job_id):
        job = self.repo.get(job_id, user_id)
        if job is None:
            raise UserException(404, 'Job not found')
        profile = self.db.scalar(select(Profile).where(Profile.user_id == user_id))
        return job, profile

    def get(self, user_id, job_id, version_id):
        row = self.db.scalar(select(TailoredResume).where(TailoredResume.id == version_id,
            TailoredResume.user_id == user_id, TailoredResume.job_id == job_id))
        if row is None:
            raise UserException(404, 'Tailored resume not found')
        return row

    def response(self, row):
        job, profile = self.source(row.user_id, row.job_id)
        result = TailoringResponse.model_validate(row)
        if row.data:
            result.pdf_filename = resume_filename(row.data, row.job_snapshot.get("company"))
        if row.status == "approved" and approval_path(row).is_file():
            result.saved_pdf = str(approval_path(row).relative_to(settings.APPROVED_RESUME_DIR))
        result.stale = not profile or profile.revision != row.profile_revision or job.revision != row.job_revision
        return result

    def listing(self, user_id, job_id, offset=0):
        job, profile = self.source(user_id, job_id)
        query = select(TailoredResume).where(TailoredResume.user_id == user_id, TailoredResume.job_id == job_id)
        rows = self.db.scalars(query.order_by(TailoredResume.id.desc()).offset(offset).limit(10)).all()
        return dict(configured=tailoring_ai.configured(), profile_revision=profile.revision if profile else None,
            job_revision=job.revision, has_description=bool(job.description and len(job.description.strip()) >= 40),
            items=[dict(id=row.id, status=row.status, created_at=row.created_at, error=row.error) for row in rows],
            total=self.db.scalar(select(func.count()).select_from(query.subquery())), offset=offset, limit=10)

    def generate(self, user_id, job_id, request):
        try:
            self.repo.lock_owner(user_id)
            existing = self.db.scalar(select(TailoredResume).where(TailoredResume.user_id == user_id,
                TailoredResume.request_id == str(request.request_id)))
            if existing:
                if existing.job_id != job_id:
                    raise UserException(409, 'This request identifier was already used for another job.')
                self.db.commit()
                return self.response(existing)
            recent = utc_now() - timedelta(minutes=2)
            if self.db.scalar(select(TailoredResume.id).where(TailoredResume.user_id == user_id,
                    TailoredResume.status == 'generating', TailoredResume.created_at > recent).limit(1)):
                raise UserException(409, 'A resume is already generating. Refresh versions before starting another.')
            job, profile = self.source(user_id, job_id)
            if not profile:
                raise UserException(422, 'Review and save your profile before tailoring a resume.')
            if profile.revision != request.profile_revision or job.revision != request.job_revision:
                raise UserException(409, 'Your profile or job changed. Refresh before generating a version.')
            if not job.description or len(job.description.strip()) < 40:
                raise UserException(422, 'Add the full job description before tailoring a resume.')
            if not tailoring_ai.configured():
                raise UserException(503, 'Configure OPENAI_API_KEY and OPENAI_MODEL on the backend first.')
            source = ProfileData.model_validate(profile.data).model_dump(mode='json')
            if not facts_for(source):
                raise UserException(422, 'Add skills, experience, education, or projects to your reviewed profile first.')
            row = TailoredResume(user_id=user_id, job_id=job_id, request_id=str(request.request_id),
                profile_revision=profile.revision, job_revision=job.revision, profile_snapshot=source,
                job_snapshot={key:getattr(job,key) for key in ('title','company','description','skills','location','work_mode')},
                section_order=SECTIONS.copy(), model=tailoring_ai.settings.OPENAI_MODEL, prompt_version=tailoring_ai.PROMPT_VERSION)
            self.db.add(row)
            self.db.commit()
        except Exception as error:
            JobService(self.repo).handle_error(error)
        # No owner lock or long-running transaction while waiting for the provider.
        row_id = row.id
        source = deepcopy(row.profile_snapshot)
        job_input = deepcopy(row.job_snapshot)
        self.db.rollback()
        try:
            public_source = deepcopy(source)
            public_source.pop('contact', None)
            for project in public_source['projects']:
                project.pop('links', None)
            proposal = tailoring_ai.generate_proposal(facts_for(source), public_source, job_input)
            data = assemble(source, proposal)
            row = self.get(user_id, job_id, row_id)
            row.proposal = proposal.model_dump(mode='json')
            row.data = data
            row.section_order = proposal.section_order
            row.status = 'draft'
            self.db.commit()
            return self.response(row)
        except Exception as error:
            self.db.rollback()
            row = self.get(user_id, job_id, row_id)
            row.status = 'failed'
            row.error = error.message if isinstance(error, UserException) else 'Generation failed. Please try a new version.'
            self.db.commit()
            if isinstance(error, UserException):
                raise
            raise UserException(502, row.error) from None

    def save(self, user_id, job_id, version_id, request):
        stored_path = None
        committed = False
        try:
            self.repo.lock_owner(user_id)
            row = self.get(user_id, job_id, version_id)
            if row.status not in {'draft','approved'}:
                raise UserException(409, 'Only a completed draft can be edited.')
            if row.revision != request.expected_revision:
                raise UserException(409, 'This resume changed in another tab. Reload it before saving.')
            if request.approve and self.response(row).stale:
                raise UserException(409, 'Your profile or job changed. Generate a new version before approval.')
            validate_order(request.section_order)
            if len(request.data.model_dump_json()) > 100000:
                raise UserException(422, 'This resume is too long. Shorten it before saving.')
            if request.approve and not request.data.contact.name:
                raise UserException(422, 'Add your name before approving this resume.')
            row.data = request.data.model_dump(mode='json')
            row.section_order = request.section_order
            row.revision += 1
            row.status = 'approved' if request.approve else 'draft'
            row.approved_at = utc_now() if request.approve else None
            if request.approve:
                try:
                    stored_path = store_approved_pdf(row)
                except ValueError:
                    raise UserException(422, 'This resume cannot fit one readable page. Shorten the summary or bullets, then approve again.') from None
                except (RuntimeError, OSError):
                    raise UserException(503, 'Could not save the approved PDF. Your draft is unchanged; please try again.') from None
            self.db.commit()
            committed = True
            return self.response(row)
        except Exception as error:
            if stored_path is not None and not committed:
                stored_path.unlink(missing_ok=True)
            JobService(self.repo).handle_error(error)

    def discard(self, user_id, job_id, version_id, expected_revision):
        """Permanently remove an unwanted draft, never an approved/in-flight version."""
        try:
            self.repo.lock_owner(user_id)
            row = self.get(user_id, job_id, version_id)
            if row.revision != expected_revision:
                raise UserException(409, 'This resume changed in another tab. Refresh before discarding it.')
            if row.status not in {'draft', 'failed'}:
                raise UserException(409, 'Only draft or failed versions can be discarded.')
            self.db.delete(row)
            self.db.commit()
        except Exception as error:
            JobService(self.repo).handle_error(error)
