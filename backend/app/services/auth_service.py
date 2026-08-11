from sqlalchemy.orm import Session

from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, LoginRequest
from app.utils.password import hash_password, verify_password


class AuthService:

    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def register(self, data: RegisterRequest):

        existing_user = self.user_repository.get_by_email(
            data.email
        )

        if existing_user:
            raise ValueError("Email already registered")

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
            raise ValueError("Invalid email or password")

        if not verify_password(data.password,user.password_hash):
            raise ValueError("Invalid email or password")

        return user