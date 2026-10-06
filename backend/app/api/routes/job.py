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
              source: Literal['manual', 'email', 'browser'] | None = None, work_mode: WorkMode | None = None,
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


from app.schemas.capture import CaptureInput, CapturePreview, CaptureDraft
from app.services.capture_service import preview_capture, save_capture_draft


@router.post('/capture/preview', response_model=CapturePreview)
def capture_preview(request: CaptureInput, user: User = Depends(get_current_user)):
    return preview_capture(request)


@router.post('/capture/drafts', response_model=JobImportResponse)
def capture_draft(request: CaptureDraft, user: User = Depends(get_current_user), service: JobService = Depends(get_job_service)):
    return save_capture_draft(service, user.id, request)


@router.post('/capture/save', response_model=JobDetail, status_code=201)
def capture_save(request: JobCreate, user: User = Depends(get_current_user), service: JobService = Depends(get_job_service)):
    return service.create(user.id, request, source_type='browser')


from app.schemas.discovered_job import DiscoveredResponse, DiscoveredPage, DiscoveryStatus
from app.services import discovered_service


@router.get('/discovered', response_model=DiscoveredPage)
def discovered_jobs(status: Literal['pending', 'dismissed', 'approved'] = 'pending',
                    site: Literal['linkedin', 'naukri', 'indeed', 'other'] | None = None,
                    limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return discovered_service.listing(db, user.id, status, limit, offset, site)


@router.post('/discovered/backfill')
def discover_existing(after_id: int = Query(0, ge=0), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return discovered_service.backfill(db, user.id, after_id)


@router.get('/discovered/lookup', response_model=list[DiscoveredResponse])
def lookup_discovery(url: str = Query(max_length=2048), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.schemas.job import validate_job_url
    from app.middlewares.exception_middleware import UserException
    try:
        validate_job_url(url)
    except ValueError:
        raise UserException(422, 'Enter a valid job URL.') from None
    return discovered_service.matching_discoveries(db, user.id, url)


@router.get('/discovered/{candidate_id}', response_model=DiscoveredResponse)
def discovered_job(candidate_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return discovered_service.get(db, user.id, candidate_id)


@router.patch('/discovered/{candidate_id}', response_model=DiscoveredResponse)
def discovery_status(candidate_id: int, request: DiscoveryStatus, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return discovered_service.set_status(db, user.id, candidate_id, request.status)


@router.post('/discovered/{candidate_id}/approve', response_model=JobDetail, status_code=201)
def approve_discovery(candidate_id: int, request: JobCreate, user: User = Depends(get_current_user), service: JobService = Depends(get_job_service)):
    return service.create(user.id, request, source_type='email', candidate_id=candidate_id)


@router.get('/{job_id}', response_model=JobDetail)
def get_job(job_id: int, user: User = Depends(get_current_user), service: JobService = Depends(get_job_service)):
    return service.get(job_id, user.id)


@router.put('/{job_id}', response_model=JobDetail)
def update_job(job_id: int, request: JobUpdate, user: User = Depends(get_current_user), service: JobService = Depends(get_job_service)):
    return service.update(job_id, user.id, request)
