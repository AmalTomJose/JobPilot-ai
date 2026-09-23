from sqlalchemy.exc import DBAPIError
from app.middlewares.exception_middleware import UserException
from app.models.profile import Profile
from app.models.resume_parse import utc_now
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import ProfileSave


class ProfileService:
    def __init__(self, repository: ProfileRepository):
        self.repository = repository

    def get(self, user_id):
        profile = self.repository.get(user_id)
        if profile is None:
            raise UserException(404, 'You have not confirmed a profile yet')
        return profile

    def save(self, user_id: int, request: ProfileSave):
        try:
            if self.repository.lock_owner(user_id) is None:
                raise UserException(404, 'Account not found')
            profile = self.repository.get(user_id)
            if request.expected_revision != (profile.revision if profile else 0):
                raise UserException(409, 'Your profile changed in another tab. Reload the latest profile before saving again; your current edits are still on this page.')
            same_source = profile is not None and profile.source_resume_id == request.source_resume_id
            parser_version = profile.source_parser_version if profile else None
            if request.source_resume_id is not None:
                resume = self.repository.resumes.owned_resume(request.source_resume_id, user_id, lock=True)
                if resume is None:
                    raise UserException(404, 'Resume not found')
                if not same_source:
                    parsed = self.repository.resumes.get(resume.id)
                    if parsed is None or parsed.status != 'completed' or parsed.draft_data is None:
                        raise UserException(409, 'Build a completed draft for this resume before reviewing it')
                    parser_version = parsed.parser_version
            elif not same_source:
                raise UserException(422, 'Choose a parsed resume to create your profile')
            if profile is None:
                profile = Profile(user_id=user_id, revision=0)
                self.repository.add(profile)
            profile.source_resume_id = request.source_resume_id
            profile.source_parser_version = parser_version
            profile.data = request.data.model_dump(mode='json')
            profile.revision += 1
            profile.updated_at = utc_now()
            self.repository.commit()
            return profile
        except DBAPIError as error:
            self.repository.rollback()
            if getattr(error.orig, 'sqlstate', None) == '55P03':
                raise UserException(409, 'This profile or resume is being updated. Please try saving again shortly') from error
            raise
        except Exception:
            self.repository.rollback()
            raise
