from sqlalchemy.orm import Session

from app.core.security import (
    get_password_hash,
    verify_password,
    verify_password_with_dummy,
)
from app.crud import crud_user
from app.models.user import User
from app.schemas.user import UserCreate, UserPasswordUpdate


def create_user(db: Session, user_in: UserCreate) -> User:
    password_hash = get_password_hash(user_in.password)

    return crud_user.create_user(db, user_in, password_hash)


def change_user_password(
    db: Session,
    db_user: User,
    password_in: UserPasswordUpdate
) -> User:
    if not verify_password(password_in.current_password, db_user.password_hash):
        raise ValueError("Current password is incorrect.")

    new_password_hash = get_password_hash(password_in.new_password)

    return crud_user.update_user_password(db, db_user, new_password_hash)


def authenticate_user(
    db: Session,
    email: str,
    password: str
) -> User | None:
    db_user = crud_user.get_user_by_email(db, email)

    if db_user is None:
        verify_password_with_dummy(password)
        return None

    if not verify_password(password, db_user.password_hash):
        return None

    return db_user
