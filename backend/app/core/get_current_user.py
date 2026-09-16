from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError, ExpiredSignatureError

from app.core.dependencies import get_db
from app.core.config import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.middlewares.exception_middleware import UserException

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise UserException(401, "Please sign in to continue")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
        user_id = int(payload["sub"])
        if user_id <= 0:
            raise ValueError("Invalid subject")
    except ExpiredSignatureError:
        raise UserException(401, "Your session expired. Please sign in again")
    except (JWTError, ValueError, TypeError, KeyError):
        raise UserException(401, "Invalid session. Please sign in again")
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise UserException(401, "This account is no longer available")
    return user
