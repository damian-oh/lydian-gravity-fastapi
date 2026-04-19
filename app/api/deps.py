from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud import crud_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenPayload

SessionDep = Annotated[Session, Depends(get_db)]

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
)
TokenDep = Annotated[str, Depends(oauth2_scheme)]


async def get_current_user(db: SessionDep, token: TokenDep) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        token_data = TokenPayload(sub=payload.get("sub"))
    except (InvalidTokenError, ValidationError):
        raise credentials_exception from None

    if token_data.sub is None:
        raise credentials_exception

    try:
        user_id = int(token_data.sub)
    except ValueError:
        raise credentials_exception from None

    db_user = crud_user.get_user(db, user_id=user_id)
    if db_user is None:
        raise credentials_exception

    return db_user


CurrentUser = Annotated[User, Depends(get_current_user)]
