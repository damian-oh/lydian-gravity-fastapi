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
from app.services import demo_service, user_service
from app.services.demo_service import DemoThrottleError

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


@router.post("/demo-session", response_model=Token)
async def create_demo_session(db: SessionDep) -> Token:
    if not settings.DEMO_MODE:
        # 404 rather than 403 so the route is indistinguishable from one that
        # does not exist when demo mode is off.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found",
        )

    try:
        return demo_service.provision_demo_session(db)
    except DemoThrottleError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many demo sessions have been created. Try again later.",
        ) from None
