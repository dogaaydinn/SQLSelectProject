"""
Security utilities for authentication and authorization
Provides JWT token generation, password hashing, and RBAC
"""

from datetime import datetime, timedelta
from typing import Any, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, ApiKey

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)

# HTTP Bearer for API key authentication
http_bearer = HTTPBearer(auto_error=False)


# ====================
# Password Hashing
# ====================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


# ====================
# JWT Token Generation
# ====================

def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict] = None,
) -> str:
    """
    Create JWT access token.

    Args:
        subject: Subject (usually user ID or username)
        expires_delta: Token expiration time
        additional_claims: Additional claims to include in token

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=settings.JWT_EXPIRATION)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow(),
        "type": "access",
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT refresh token.

    Args:
        subject: Subject (usually user ID or username)
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRATION)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow(),
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and verify JWT token.

    Args:
        token: JWT token

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ====================
# API Key Hashing
# ====================

def hash_api_key(api_key: str) -> str:
    """
    Hash an API key.

    Args:
        api_key: Plain text API key

    Returns:
        Hashed API key
    """
    return pwd_context.hash(api_key)


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against a hash.

    Args:
        plain_key: Plain text API key
        hashed_key: Hashed API key

    Returns:
        True if key matches, False otherwise
    """
    return pwd_context.verify(plain_key, hashed_key)


# ====================
# Authentication Dependencies
# ====================

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
        token_type: str = payload.get("type")

        if username is None or token_type != "access":
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Get user from database
    query = select(User).where(
        and_(User.username == username, User.is_active == True)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    # Check if account is locked
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked. Please contact administrator.",
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        Current user or None
    """
    if not token:
        return None

    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user and verify they are a superuser.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user (if superuser)

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )
    return current_user


# ====================
# Authorization (RBAC)
# ====================

class PermissionChecker:
    """
    Dependency to check if user has required permissions.

    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            user: User = Depends(PermissionChecker(["admin:read", "admin:write"]))
        ):
            ...
    """

    def __init__(self, required_permissions: list[str], require_all: bool = True):
        """
        Initialize permission checker.

        Args:
            required_permissions: List of required permissions
            require_all: If True, user must have ALL permissions. If False, user must have ANY permission.
        """
        self.required_permissions = required_permissions
        self.require_all = require_all

    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
    ) -> User:
        """
        Check if user has required permissions.

        Args:
            current_user: Current authenticated user

        Returns:
            Current user (if authorized)

        Raises:
            HTTPException: If user doesn't have required permissions
        """
        # Superusers always have all permissions
        if current_user.is_superuser:
            return current_user

        # Check permissions
        if self.require_all:
            # User must have ALL required permissions
            for permission in self.required_permissions:
                if not current_user.has_permission(permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required permission: {permission}",
                    )
        else:
            # User must have ANY of the required permissions
            has_permission = any(
                current_user.has_permission(perm) for perm in self.required_permissions
            )
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions: {', '.join(self.required_permissions)}",
                )

        return current_user


class RoleChecker:
    """
    Dependency to check if user has required roles.

    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            user: User = Depends(RoleChecker(["admin", "manager"]))
        ):
            ...
    """

    def __init__(self, required_roles: list[str], require_all: bool = False):
        """
        Initialize role checker.

        Args:
            required_roles: List of required roles
            require_all: If True, user must have ALL roles. If False, user must have ANY role.
        """
        self.required_roles = required_roles
        self.require_all = require_all

    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
    ) -> User:
        """
        Check if user has required roles.

        Args:
            current_user: Current authenticated user

        Returns:
            Current user (if authorized)

        Raises:
            HTTPException: If user doesn't have required roles
        """
        # Superusers always have access
        if current_user.is_superuser:
            return current_user

        # Check roles
        if self.require_all:
            # User must have ALL required roles
            for role in self.required_roles:
                if not current_user.has_role(role):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required role: {role}",
                    )
        else:
            # User must have ANY of the required roles
            has_role = any(current_user.has_role(role) for role in self.required_roles)
            if not has_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required roles: {', '.join(self.required_roles)}",
                )

        return current_user


# ====================
# API Key Authentication
# ====================

async def get_api_key_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Authenticate user via API key.

    Args:
        credentials: HTTP Authorization credentials
        db: Database session

    Returns:
        User associated with API key

    Raises:
        HTTPException: If API key is invalid
    """
    if not credentials:
        return None

    api_key = credentials.credentials

    # Query all active API keys
    query = select(ApiKey).where(ApiKey.is_active == True)
    result = await db.execute(query)
    api_keys = result.scalars().all()

    # Check each key
    for key_record in api_keys:
        if verify_api_key(api_key, key_record.key_hash):
            # Check if key is expired
            if key_record.is_expired:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key has expired",
                )

            # Update last used
            key_record.last_used_at = datetime.utcnow()
            await db.commit()

            # Get user
            user_query = select(User).where(User.id == key_record.user_id)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()

            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is inactive",
                )

            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


async def get_current_user_or_api_key(
    user_from_token: Optional[User] = Depends(get_current_user_optional),
    user_from_api_key: Optional[User] = Depends(get_api_key_user),
) -> User:
    """
    Get current user from either JWT token or API key.

    Args:
        user_from_token: User from JWT token
        user_from_api_key: User from API key

    Returns:
        Authenticated user

    Raises:
        HTTPException: If neither authentication method succeeds
    """
    user = user_from_token or user_from_api_key

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
