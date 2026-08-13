from sqlalchemy.orm import Session

from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, LoginRequest
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token

from app.middlewares.exception_middleware import UserException


class AuthService:

    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def register(self, data: RegisterRequest):

        existing_user = self.user_repository.get_by_email(
            data.email
        )

        if existing_user:
           raise UserException(
                status_code=409,
                message="Email already registered"
            )

        password_hash = hash_password(data.password)

        user = self.user_repository.create(
            name=data.name,
            email=data.email,
            password_hash=password_hash
        )

        return user
    
    def login(self,data:LoginRequest):
        user = self.user_repository.get_by_email(data.email)

        if not user:
            raise UserException(
                status_code=401,
                message="Invalid email or password"
            )

        if not verify_password(data.password,user.password_hash):
            raise UserException(
                status_code=401,
                message="Invalid email or password"
            )
        
        access_token = create_access_token(user.id)
        
        return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
        }
