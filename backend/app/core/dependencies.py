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