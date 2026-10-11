import logging
from typing import Annotated

from backend.app.core.config import settings
from backend.app.core.security import decode_access_token, hash_password
from backend.app.db.session import get_db
from backend.app.models.domain import User
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

security_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Validate Bearer JWT and return authenticated User record."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated.",
        )

    return user


def require_staff(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Enforce that caller has at least staff role."""
    if current_user.role not in ("staff", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff credentials required to access this resource.",
        )
    return current_user


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Enforce administrative role for sensitive configuration changes."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required for this action.",
        )
    return current_user


def ensure_initial_admin(db: Session) -> User | None:
    """Ensure the configured initial administrator from environment exists with active admin role."""
    if not settings.initial_admin_email:
        return None

    admin_user = db.scalar(select(User).where(User.email == settings.initial_admin_email))
    if not admin_user:
        if not settings.initial_admin_password:
            user_count = db.scalar(select(func.count(User.id))) or 0
            if user_count == 0:
                raise RuntimeError(
                    "INITIAL_ADMIN_PASSWORD must be configured before creating the initial admin."
                )
            return None
        admin_user = User(
            email=settings.initial_admin_email,
            hashed_password=hash_password(settings.initial_admin_password),
            full_name="SlotBack Administrator",
            role="admin",
            business_id="1",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        logger.info(
            "Initial administrator created successfully with email: %s",
            settings.initial_admin_email,
        )
        return admin_user

    # Invariant: If administrator already exists, do not reset or overwrite their password on restart.
    # Preserve active status and role without altering credentials.
    if admin_user.role != "admin" or not admin_user.is_active:
        admin_user.role = "admin"
        admin_user.is_active = True
        db.commit()
        db.refresh(admin_user)
    return admin_user
