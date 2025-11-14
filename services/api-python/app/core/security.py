"""
Security Module
Handles authentication, authorization, password hashing, and JWT tokens
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)

# API Key header
api_key_header = APIKeyHeader(
    name=settings.API_KEY_HEADER,
    auto_error=False,
)


class PasswordHasher:
    """Password hashing utilities."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)


class JWTHandler:
    """JWT token utilities."""

    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create JWT access token.

        Args:
            data: Data to encode in token
            expires_delta: Token expiration time

        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                seconds=settings.JWT_EXPIRATION
            )

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
        })

        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create JWT refresh token.

        Args:
            data: Data to encode in token
            expires_delta: Token expiration time

        Returns:
            Encoded JWT refresh token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                seconds=settings.REFRESH_TOKEN_EXPIRATION
            )

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
        })

        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode JWT token.

        Args:
            token: JWT token to decode

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        except JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


class RBACHandler:
    """Role-Based Access Control utilities."""

    @staticmethod
    async def check_permission(
        user_id: int,
        required_permission: str,
        db: AsyncSession,
    ) -> bool:
        """
        Check if user has required permission.

        Args:
            user_id: User ID
            required_permission: Required permission string
            db: Database session

        Returns:
            True if user has permission
        """
        # Import here to avoid circular imports
        from app.models.user import User, UserRole, Role

        # Get user with roles
        query = (
            select(User)
            .where(User.id == user_id)
            .where(User.is_active == True)
        )
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return False

        # Superuser has all permissions
        if user.is_superuser:
            return True

        # Get user's roles
        query = (
            select(Role)
            .join(UserRole)
            .where(UserRole.user_id == user_id)
            .where(Role.is_active == True)
        )
        result = await db.execute(query)
        roles = result.scalars().all()

        # Check if any role has the required permission
        for role in roles:
            permissions = role.permissions or []
            if "*" in permissions or required_permission in permissions:
                return True

        return False

    @staticmethod
    def require_permission(permission: str):
        """
        Decorator to require specific permission.

        Usage:
            @require_permission("employees:write")
            async def create_employee(...):
                ...
        """
        async def permission_checker(
            current_user: dict = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
        ):
            has_permission = await RBACHandler.check_permission(
                current_user["id"],
                permission,
                db,
            )
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission} required",
                )
            return current_user

        return permission_checker


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get current authenticated user.

    Supports both JWT token and API key authentication.

    Args:
        token: JWT access token
        api_key: API key
        db: Database session

    Returns:
        Current user information

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try JWT token first
    if token:
        try:
            payload = JWTHandler.decode_token(token)

            # Verify token type
            if payload.get("type") != "access":
                raise credentials_exception

            user_id: int = payload.get("sub")
            if user_id is None:
                raise credentials_exception

            # Import here to avoid circular imports
            from app.models.user import User

            # Get user from database
            query = select(User).where(User.id == user_id).where(User.is_active == True)
            result = await db.execute(query)
            user = result.scalar_one_or_none()

            if user is None:
                raise credentials_exception

            # Update last login
            user.last_login = datetime.utcnow()
            await db.commit()

            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_superuser": user.is_superuser,
            }

        except JWTError:
            raise credentials_exception

    # Try API key
    elif api_key:
        from app.models.user import APIKey, User
        import hashlib

        # Hash the API key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Find API key in database
        query = (
            select(APIKey)
            .where(APIKey.key_hash == key_hash)
            .where(APIKey.is_active == True)
        )
        result = await db.execute(query)
        api_key_obj = result.scalar_one_or_none()

        if not api_key_obj:
            raise credentials_exception

        # Check expiration
        if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired",
            )

        # Get user
        query = select(User).where(User.id == api_key_obj.user_id).where(User.is_active == True)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise credentials_exception

        # Update last used
        api_key_obj.last_used_at = datetime.utcnow()
        await db.commit()

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_superuser": user.is_superuser,
            "api_key": True,
        }

    else:
        raise credentials_exception


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get current active user (convenience function)."""
    return current_user


async def get_current_superuser(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current user and verify superuser status.

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return current_user
