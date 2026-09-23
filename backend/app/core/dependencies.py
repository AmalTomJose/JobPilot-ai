from app.repositories.profile_repository import ProfileRepository
from app.services.profile_service import ProfileService
from app.repositories.resume_parse_repository import ResumeParseRepository
from app.services.resume_parse_service import ResumeParseService
from app.database.database import SessionLocal

#Dependency injections:
from fastapi import Depends
from sqlalchemy.orm import Session

#service
from app.services.resume_service import ResumeService

#repository
from app.repositories.resume_repository import ResumeRepository


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def get_resume_service(
    db: Session = Depends(get_db)
) -> ResumeService:

    repository = ResumeRepository(db)

    return ResumeService(repository)



def get_resume_parse_service(db: Session = Depends(get_db)) -> ResumeParseService:
    return ResumeParseService(ResumeParseRepository(db))


def get_profile_service(db: Session = Depends(get_db)) -> ProfileService:
    return ProfileService(ProfileRepository(db))
