from hashlib import sha256
from sqlalchemy.exc import DBAPIError
from app.middlewares.exception_middleware import UserException
from app.models.resume_parse import ResumeParse, utc_now
from app.repositories.resume_parse_repository import ResumeParseRepository
from app.services.resume_parser import parse_resume, PARSER_VERSION, MAX_TEXT_LENGTH


class ResumeParseService:
    def __init__(self, repository: ResumeParseRepository):
        self.repository = repository

    def get(self, resume_id: int, user_id: int):
        if self.repository.owned_resume(resume_id, user_id) is None:
            raise UserException(404, 'Resume not found')
        record = self.repository.get(resume_id)
        if record is None:
            raise UserException(404, 'This resume has not been parsed yet')
        return record

    def parse(self, resume_id: int, user_id: int, force=False):
        try:
            resume = self.repository.owned_resume(resume_id, user_id, lock=True)
            if resume is None:
                raise UserException(404, 'Resume not found')
            text = resume.raw_text
            if not text or not text.strip():
                raise UserException(422, 'This resume has no extracted text to parse')
            if len(text) > MAX_TEXT_LENGTH:
                raise UserException(413, 'Resume text exceeds the 200,000-character parsing limit')
            fingerprint = sha256(text.encode('utf-8')).hexdigest()
            record = self.repository.get(resume_id)
            if (record and not force and record.status == 'completed'
                    and record.source_hash == fingerprint and record.parser_version == PARSER_VERSION):
                self.repository.commit()  # Release the parent lock on cached requests too.
                return record
            if record is None:
                record = ResumeParse(resume_id=resume_id, parser_version=PARSER_VERSION,
                                     source_hash=fingerprint, warnings=[])
                self.repository.add(record)
            record.status = 'processing'
            record.parser_version = PARSER_VERSION
            record.source_hash = fingerprint
            record.draft_data = None
            record.warnings = []
            record.error_message = None
            record.completed_at = None
            try:
                result = parse_resume(text)
                record.draft_data = result.draft.model_dump(mode='json')
                record.warnings = [warning.model_dump() for warning in result.warnings]
                record.status = 'completed'
            except Exception:
                # Save failure without leaking source text or internal exception details.
                record.status = 'failed'
                record.error_message = 'Parsing could not finish. You can retry this resume.'
            record.completed_at = utc_now()
            self.repository.commit()
            return record
        except DBAPIError as error:
            self.repository.rollback()
            if getattr(error.orig, 'sqlstate', None) == '55P03':
                raise UserException(409, 'This resume is already being parsed. Please try again shortly') from error
            raise
        except Exception:
            self.repository.rollback()
            raise
