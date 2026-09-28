from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.core.get_current_user import get_current_user
from app.models.user import User
from app.repositories.match_repository import MatchRepository
from app.services.match_service import MatchService
from app.schemas.job_match import MatchPage, MatchRun

router = APIRouter(prefix='/matches', tags=['Matches'])


def service(db: Session = Depends(get_db)):
    return MatchService(MatchRepository(db))


@router.get('', response_model=MatchPage)
def list_matches(include_archived: bool = False, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                 user: User = Depends(get_current_user), matcher: MatchService = Depends(service)):
    return matcher.list(user.id, include_archived, limit, offset)


@router.post('/run', response_model=MatchRun)
def run_matches(user: User = Depends(get_current_user), matcher: MatchService = Depends(service)):
    return matcher.run(user.id)
