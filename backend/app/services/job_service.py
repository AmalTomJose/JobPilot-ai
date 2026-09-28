from hashlib import sha256
from sqlalchemy.exc import DBAPIError, IntegrityError
from app.middlewares.exception_middleware import UserException
from app.models.job import Job, JobImport
from app.models.resume_parse import utc_now
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobCreate, JobUpdate, JobSummary, JobDetail, JobImportResponse, DuplicateJob
from app.services.job_parser import parse_job_email, canonical_url, PARSER_VERSION


def url_fingerprint(value):
    normalized = canonical_url(value)
    return sha256(normalized.encode()).hexdigest() if normalized else None


class JobService:
    def __init__(self, repository: JobRepository):
        self.repository = repository

    def duplicate_info(self, row, import_id=None):
        return DuplicateJob(id=row.id, title=row.title, company=row.company,
                            reason='This email has already been saved as a job.' if import_id and row.source_import_id == import_id else 'A job with this application URL is already saved (including archived jobs).')

    def import_response(self, row):
        result = JobImportResponse.model_validate(row)
        duplicate = self.repository.duplicate(row.user_id, url_fingerprint(row.draft_data.get('application_url')), row.id)
        if duplicate:
            result.duplicate = self.duplicate_info(duplicate, row.id)
        return result

    def get_import(self, import_id, user_id):
        row = self.repository.get_import(import_id, user_id)
        if row is None:
            raise UserException(404, 'Email import not found')
        return self.import_response(row)

    def detail(self, row):
        result = JobDetail.model_validate(row)
        if row.source_import_id:
            source = self.repository.get_import(row.source_import_id, row.user_id)
            if source:
                result.source = JobImportResponse.model_validate(source)
        return result

    def get(self, job_id, user_id):
        row = self.repository.get(job_id, user_id)
        if row is None:
            raise UserException(404, 'Job not found')
        return self.detail(row)

    def handle_error(self, error):
        self.repository.rollback()
        if isinstance(error, IntegrityError):
            raise UserException(409, 'This job or email was saved in another request. Refresh the inbox to find the existing record.') from error
        if isinstance(error, DBAPIError) and getattr(error.orig, 'sqlstate', None) == '55P03':
            raise UserException(409, 'Another save is in progress. Please try again shortly.') from error
        raise error

    def import_email(self, user_id, raw_text):
        try:
            self.repository.lock_owner(user_id)
            fingerprint = sha256(raw_text.encode()).hexdigest()
            row = self.repository.import_by_hash(user_id, fingerprint)
            if row is None:
                result = parse_job_email(raw_text)
                row = JobImport(user_id=user_id, raw_text=raw_text, source_hash=fingerprint,
                                parser_version=result.parser_version, draft_data=result.draft_data.model_dump(mode='json'),
                                warnings=[warning.model_dump() for warning in result.warnings])
                self.repository.add(row)
            elif row.parser_version != PARSER_VERSION and self.repository.duplicate(user_id, None, row.id) is None:
                # Explicitly pasting/extracting again refreshes an unsaved draft.
                # Imports attached to saved jobs retain their original provenance.
                result = parse_job_email(row.raw_text)
                row.parser_version = result.parser_version
                row.draft_data = result.draft_data.model_dump(mode='json')
                row.warnings = [warning.model_dump() for warning in result.warnings]
            self.repository.commit()
            return self.import_response(row)
        except Exception as error:
            self.handle_error(error)

    def check_duplicate(self, user_id, fingerprint, import_id=None, exclude_id=None):
        row = self.repository.duplicate(user_id, fingerprint, import_id, exclude_id)
        if row:
            info = self.duplicate_info(row, import_id)
            raise UserException(409, info.reason, details={'duplicate': info.model_dump()})

    def create(self, user_id, request: JobCreate):
        try:
            self.repository.lock_owner(user_id)
            if request.import_id and self.repository.get_import(request.import_id, user_id) is None:
                raise UserException(404, 'Email import not found')
            fingerprint = url_fingerprint(request.application_url)
            self.check_duplicate(user_id, fingerprint, request.import_id)
            row = Job(user_id=user_id, source_import_id=request.import_id,
                      source_type='email' if request.import_id else 'manual', url_hash=fingerprint,
                      **request.model_dump(exclude={'import_id'}))
            self.repository.add(row)
            self.repository.commit()
            return self.detail(row)
        except Exception as error:
            self.handle_error(error)

    def update(self, job_id, user_id, request: JobUpdate):
        try:
            self.repository.lock_owner(user_id)
            row = self.repository.get(job_id, user_id)
            if row is None:
                raise UserException(404, 'Job not found')
            if row.revision != request.expected_revision:
                raise UserException(409, 'This job changed in another tab. Your edits are still here; reopen the job to load its latest version.')
            fingerprint = url_fingerprint(request.application_url)
            self.check_duplicate(user_id, fingerprint, exclude_id=job_id)
            for field, value in request.model_dump(exclude={'expected_revision'}).items():
                setattr(row, field, value)
            row.url_hash = fingerprint
            row.revision += 1
            row.updated_at = utc_now()
            self.repository.commit()
            return self.detail(row)
        except Exception as error:
            self.handle_error(error)
