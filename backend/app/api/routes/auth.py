from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.auth import RegisterRequest,LoginRequest
from app.services.auth_service import AuthService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)



@router.post("/register")
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):

    service = AuthService(db)

    try:

        user = service.register(data)

        return {
            "message": "Registration successful",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }

    except ValueError as error:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error)
        )
@router.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):

    service = AuthService(db)

    try:

        user = service.login(data)

        return user

    except ValueError as error:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error)
        )