from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.middlewares.exception_middleware import UserException

from app.models.user import User


class UserRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        user = select(User).where(User.email == email)

        return self.db.scalar(user)
    
    def get_by_id(self, user_id: int) -> User | None:
       return self.db.get(User, user_id)
    
    def create(
        self,
        name: str,
        email: str,
        password_hash: str
    ) -> User:

        user = User(
            name=name,
            email=email,
            password_hash=password_hash
        )

        try:
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            if self.get_by_email(email) is not None:
                raise UserException(409, "Email already registered") from error
            raise
        except Exception:
            self.db.rollback()
            raise

        return user
    
    