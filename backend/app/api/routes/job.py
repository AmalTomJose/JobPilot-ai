from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.core.get_current_user import get_current_user
from app.models.user import User
from app.repositories.job_repository import JobRepository
from app.services.job_service import JobService
from app.schemas.job import EmailImportRequest, JobCreate, JobUpdate, JobDetail, JobPage, JobImportResponse, ImportPage, WorkMode, JobStatus

router = APIRouter(prefix='/jobs', tags=['Jobs'])


def get_job_service(db: Session = Depends(get_db)):
    return JobService(JobRepository(db))


@router.get('', response_model=JobPage)
def list_jobs(q: str = Query('', max_length=200), status: JobStatus | None = None,
              source: Literal['manual', 'email'] | None = None, work_mode: WorkMode | None = None,
              limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
              user: User = Depends(get_current_user), service: JobService = Depends(get_job_service)):
    return service.repository.list(user.id, q.strip(), status, source, work_mode, limit, offset)


@router.post('', response_model=JobDetail, status_code=201)
def create_job(request: JobCreate, user: User = Depends(get_current_user), service: JobService = Depends(get_job_service)):
    return service.create(user.id, request)


@router.get('/imports', response_model=ImportPage)
def list_imports(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                 user: User = Depends(get_current_user), service: JobService = Depends(get_job_service)):
    return service.repository.imports(user.id, limit, offset)


@router.post('/imports', response_model=JobImportResponse)
def import_email(request: EmailImportRequest, user: User = Depends(get_current_user), service: JobService = Depends(get_job_service)):
    return service.import_email(user.id, request.raw_text)


@router.get('/imports/{import_id}', response_model=JobImportResponse)
def get_import(import_id: int, user: User = Depends(get_current_user), service: JobService = Depends(get_job_service)):
    return service.get_import(import_id, user.id)


@router.get('/{job_id}', response_model=JobDetail)
def get_job(job_id: int, user: User = Depends(get_current_user), service: JobService = Depends(get_job_service)):
    return service.get(job_id, user.id)


@router.put('/{job_id}', response_model=JobDetail)
def update_job(job_id: int, request: JobUpdate, user: User = Depends(get_current_user), service: JobService = Depends(get_job_service)):
    return service.update(job_id, user.id, request)
