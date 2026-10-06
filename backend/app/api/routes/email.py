from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError
from app.core.config import settings
from app.core.dependencies import get_db
from app.core.get_current_user import get_current_user
from app.models.user import User
from app.repositories.email_repository import EmailRepository
from app.services.email_service import EmailService
from app.schemas.email import GmailStatus, GmailSelection, GmailLabel, SyncRunResponse, EmailPage
from app.middlewares.exception_middleware import UserException

router = APIRouter(prefix='/email/gmail', tags=['Gmail'])
COOKIE = 'jobpilot_gmail_oauth'
COOKIE_PATH = '/email/gmail'


def service(db: Session = Depends(get_db)):
    try:
        yield EmailService(EmailRepository(db))
    except DBAPIError as error:
        db.rollback()
        if getattr(error.orig, 'sqlstate', None) == '55P03':
            raise UserException(409, 'Another Gmail operation is running. Please try again shortly.') from error
        raise


@router.get('', response_model=GmailStatus)
def status(user: User = Depends(get_current_user), email: EmailService = Depends(service)):
    return email.status(user.id)


@router.post('/connect')
def connect(response: Response, user: User = Depends(get_current_user), email: EmailService = Depends(service)):
    url, browser = email.start(user.id)
    response.set_cookie(COOKIE, browser, max_age=600, httponly=True, secure=settings.GMAIL_REDIRECT_URI.startswith('https://'), samesite='lax', path=COOKIE_PATH)
    response.headers['Cache-Control'] = 'no-store'
    return {'authorization_url': url}


@router.get('/callback')
def callback(request: Request, state: str = Query('', max_length=256), code: str = Query('', max_length=4096), error: str = Query('', max_length=255), email: EmailService = Depends(service)):
    result = email.callback(state, request.cookies.get(COOKIE), code, denied=bool(error))
    response = RedirectResponse(settings.FRONTEND_URL.rstrip('/') + '/settings?gmail=' + result, status_code=303)
    response.delete_cookie(COOKIE, path=COOKIE_PATH)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@router.get('/labels', response_model=list[GmailLabel])
def labels(user: User = Depends(get_current_user), email: EmailService = Depends(service)):
    return email.labels(user.id)


@router.put('/selection', response_model=GmailStatus)
def selection(request: GmailSelection, user: User = Depends(get_current_user), email: EmailService = Depends(service)):
    return email.configure(user.id, request)


@router.post('/sync', response_model=SyncRunResponse)
def sync(user: User = Depends(get_current_user), email: EmailService = Depends(service)):
    return email.sync(user.id)


@router.delete('')
def disconnect(user: User = Depends(get_current_user), email: EmailService = Depends(service)):
    return email.disconnect(user.id)


@router.get('/messages', response_model=EmailPage)
def messages(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), user: User = Depends(get_current_user), email: EmailService = Depends(service)):
    return email.repo.messages(user.id, limit, offset)


@router.get('/runs', response_model=list[SyncRunResponse])
def runs(user: User = Depends(get_current_user), email: EmailService = Depends(service)):
    return email.repo.runs(user.id)
