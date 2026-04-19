from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.core.config import settings
from app.core.security import create_access_token
from app.crud import crud_user
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead
from app.services import user_service

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(db: SessionDep, user_in: UserCreate) -> UserRead:
    if crud_user.get_user_by_email(db, email=user_in.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    try:
        return user_service.create_user(db, user_in)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        ) from None


@router.post("/login", response_model=Token)
async def login_access_token(
    db: SessionDep,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> Token:
    user = user_service.authenticate_user(
        db,
        email=username.strip().lower(),
        password=password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return Token(access_token=access_token, token_type="bearer")
