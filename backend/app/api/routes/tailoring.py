from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.core.get_current_user import get_current_user
from app.models.user import User
from app.schemas.tailoring import GenerateTailoring, SaveTailoring, TailoringResponse
from app.services.tailoring_service import TailoringService
from app.services.tailoring_pdf import render_resume
from app.services.tailoring_storage import resume_filename
from app.middlewares.exception_middleware import UserException

router = APIRouter(prefix='/jobs/{job_id}/tailoring', tags=['Resume tailoring'])

@router.get('')
def list_versions(job_id: int, offset: int = Query(0, ge=0), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TailoringService(db).listing(user.id, job_id, offset)

@router.post('', response_model=TailoringResponse, status_code=201)
def generate(job_id: int, request: GenerateTailoring, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TailoringService(db).generate(user.id, job_id, request)

@router.get('/{version_id}', response_model=TailoringResponse)
def get_version(job_id: int, version_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = TailoringService(db)
    return service.response(service.get(user.id, job_id, version_id))

@router.put('/{version_id}', response_model=TailoringResponse)
def save_version(job_id: int, version_id: int, request: SaveTailoring, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TailoringService(db).save(user.id, job_id, version_id, request)

@router.get('/{version_id}/pdf')
def download_pdf(job_id: int, version_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = TailoringService(db)
    row = service.get(user.id, job_id, version_id)
    if row.status != 'approved':
        raise UserException(409, 'Review and approve this resume before downloading it.')
    if service.response(row).stale:
        raise UserException(409, 'The profile or job changed since this resume was generated. Create and approve a new version.')
    try:
        pdf = render_resume(row.data, row.section_order)
    except (ValueError, RuntimeError):
        raise UserException(422, 'This resume cannot fit one readable page. Shorten the summary or bullets and approve again.') from None
    return Response(pdf, media_type='application/pdf', headers={
        'Content-Disposition':f'attachment; filename="{resume_filename(row.data, row.job_snapshot.get("company"))}"',
        'Cache-Control':'no-store'})

@router.delete('/{version_id}', status_code=204)
def discard_version(job_id: int, version_id: int, expected_revision: int = Query(ge=1),
        user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    TailoringService(db).discard(user.id, job_id, version_id, expected_revision)
    return Response(status_code=204)
