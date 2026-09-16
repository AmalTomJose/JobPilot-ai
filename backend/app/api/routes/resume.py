from fastapi import APIRouter, Depends, File, UploadFile
from app.core.get_current_user import get_current_user
from app.core.dependencies import get_resume_service
from app.models.user import User
from app.services.resume_service import ResumeService
from app.schemas.resume import ResumeResponse

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/upload", response_model=ResumeResponse, status_code=201)
def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
):
    return service.upload_resume(file=file, user_id=current_user.id)
