from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_resume_parse_service
from app.repositories.resume_repository import ResumeRepository
from app.services.resume_parse_service import ResumeParseService
from app.schemas.resume_parse import ResumeParseResponse
from app.middlewares.exception_middleware import UserException
from fastapi import APIRouter, Depends, File, UploadFile, Query
from app.core.get_current_user import get_current_user
from app.core.dependencies import get_resume_service
from app.models.user import User
from app.services.resume_service import ResumeService
from app.schemas.resume import ResumeResponse, ResumeSummary

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/upload", response_model=ResumeResponse, status_code=201)
def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
):
    return service.upload_resume(file=file, user_id=current_user.id)


@router.get("", response_model=list[ResumeSummary])
def list_resumes(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
):
    return ResumeRepository(db).get_by_user_id(current_user.id, limit=limit, offset=offset)


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = ResumeRepository(db).get_by_id(resume_id, current_user.id)
    if resume is None:
        raise UserException(404, "Resume not found")
    return resume


@router.post("/{resume_id}/parse", response_model=ResumeParseResponse)
def parse_resume_draft(
    resume_id: int, force: bool = False,
    current_user: User = Depends(get_current_user),
    service: ResumeParseService = Depends(get_resume_parse_service),
):
    return service.parse(resume_id, current_user.id, force=force)


@router.get("/{resume_id}/parse", response_model=ResumeParseResponse)
def get_resume_draft(
    resume_id: int, current_user: User = Depends(get_current_user),
    service: ResumeParseService = Depends(get_resume_parse_service),
):
    return service.get(resume_id, current_user.id)
