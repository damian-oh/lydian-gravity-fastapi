from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, SessionDep
from app.crud import crud_user
from app.schemas.msg import Msg
from app.schemas.user import UserPasswordUpdate, UserRead, UserUpdate
from app.services import user_service

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: CurrentUser) -> UserRead:
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_current_user(
    db: SessionDep,
    current_user: CurrentUser,
    user_in: UserUpdate,
) -> UserRead:
    if user_in.email is not None and user_in.email != current_user.email:
        existing_user = crud_user.get_user_by_email(db, email=user_in.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

    try:
        return crud_user.update_user(db, current_user, user_in)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        ) from None


@router.post("/me/password", response_model=Msg)
def update_current_user_password(
    db: SessionDep,
    current_user: CurrentUser,
    password_in: UserPasswordUpdate,
) -> Msg:
    # def rather than async def: verifies and hashes a password, which is too
    # slow for the event loop (see create_demo_session in auth.py).
    try:
        user_service.change_user_password(db, current_user, password_in)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        ) from None

    return Msg(message="Password updated successfully.")
