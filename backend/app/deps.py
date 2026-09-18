"""Authentication and authorization dependencies.

`get_current_user` resolves the bearer token to a User.
`require_buyer` / `require_supplier` layer a role check on top, so route
handlers never have to write `if user.role != ...` themselves. Authorization
lives in one place and is impossible to forget on a new endpoint.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.security import decode_access_token

# auto_error=False so a missing header produces our own 401 shape, not FastAPI's.
bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_ERROR

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise CREDENTIALS_ERROR

    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError):
        raise CREDENTIALS_ERROR

    user = db.get(User, user_id)
    if user is None:
        # Valid signature but the account is gone - still unauthenticated.
        raise CREDENTIALS_ERROR
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_buyer(user: CurrentUser) -> User:
    if user.role != UserRole.BUYER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is only available to buyer accounts",
        )
    return user


def require_supplier(user: CurrentUser) -> User:
    if user.role != UserRole.SUPPLIER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is only available to supplier accounts",
        )
    return user


BuyerUser = Annotated[User, Depends(require_buyer)]
SupplierUser = Annotated[User, Depends(require_supplier)]
DbSession = Annotated[Session, Depends(get_db)]
