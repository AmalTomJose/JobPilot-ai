from fastapi import Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer
)
from sqlalchemy.orm import Session
from jose import jwt

from app.core.dependencies import get_db
from app.core.config import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.middlewares.exception_middleware import UserException


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise UserException(
                status_code=401,
                message="Invalid token"
            )

    except jwt.ExpiredSignatureError:

        raise UserException(
            status_code=401,
            message="Token has expired"
        )

    except jwt.InvalidTokenError:

        raise UserException(
            status_code=401,
            message="Invalid token"
        )

    repository = UserRepository(db)

    user = repository.get_by_id(int(user_id))

    if user is None:
        raise UserException(
            status_code=404,
            message="User not found"
        )

    return user