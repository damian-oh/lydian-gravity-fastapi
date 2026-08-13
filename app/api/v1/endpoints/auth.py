from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.core.config import settings
from app.core.rate_limit import RateLimitExceeded, SlidingWindowThrottle
from app.core.security import create_access_token
from app.crud import crud_user
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead
from app.services import demo_service, user_service
from app.services.demo_service import DemoThrottleError

router = APIRouter()

# Per-client sliding-window throttles guarding login/register from brute-force
# and registration spam. Same client_key derivation and reverse-proxy caveat as
# demo_service's throttle -- see app/core/config.py.
_login_throttle = SlidingWindowThrottle()
_register_throttle = SlidingWindowThrottle()


def reset_auth_throttles() -> None:
    """Clear both throttles. Used by tests."""
    _login_throttle.reset()
    _register_throttle.reset()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register_user(request: Request, db: SessionDep, user_in: UserCreate) -> UserRead:
    # def rather than async def: hashes a password (see create_demo_session).
    client_key = request.client.host if request.client else "unknown"

    try:
        _register_throttle.hit(
            client_key,
            settings.AUTH_REGISTER_MAX_ATTEMPTS_PER_WINDOW,
            settings.AUTH_REGISTER_WINDOW_SECONDS,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Try again later.",
        ) from None

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
def login_access_token(
    request: Request,
    db: SessionDep,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> Token:
    # def rather than async def: verifies a password (see create_demo_session).
    client_key = request.client.host if request.client else "unknown"

    try:
        _login_throttle.hit(
            client_key,
            settings.AUTH_LOGIN_MAX_ATTEMPTS_PER_WINDOW,
            settings.AUTH_LOGIN_WINDOW_SECONDS,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        ) from None

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


@router.post(
    "/demo-session",
    response_model=Token,
    # Hidden from the schema when the deployment has demo mode off, so the
    # documented API matches what the deployment actually serves.
    include_in_schema=settings.DEMO_MODE,
)
def create_demo_session(request: Request, db: SessionDep) -> Token:
    """Provision a throwaway account and return a real access token for it.

    Defined with def rather than async def -- like every endpoint here that
    hashes a password, because Argon2 is slow enough that running it on the
    event loop would stall every other in-flight request. FastAPI hands a def
    endpoint to the threadpool.
    """
    if not settings.DEMO_MODE:
        # 404 rather than 403 so a probe gets the same response it would get for
        # a path that is not routed at all.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found",
        )

    client_key = request.client.host if request.client else "unknown"

    try:
        return demo_service.provision_demo_session(db, client_key)
    except DemoThrottleError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many demo sessions have been created. Try again later.",
        ) from None
