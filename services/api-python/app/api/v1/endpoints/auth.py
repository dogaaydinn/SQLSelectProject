"""
Authentication API Endpoints
Provides login, registration, token refresh, and logout functionality
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, EmailStr, Field

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    get_current_user,
)
from app.models.user import User, Role
from app.utils.cache import cache_manager

router = APIRouter()


# Pydantic schemas
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    roles: list[str] = []

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        Created user
    """
    # Check if username already exists
    username_query = select(User).where(User.username == user_data.username)
    username_result = await db.execute(username_query)
    existing_user = username_result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )

    # Check if email already exists
    email_query = select(User).where(User.email == user_data.email)
    email_result = await db.execute(email_query)
    existing_email = email_result.scalar_one_or_none()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=True,
        is_superuser=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Assign default "user" role if it exists
    role_query = select(Role).where(Role.name == "user")
    role_result = await db.execute(role_query)
    default_role = role_result.scalar_one_or_none()

    if default_role:
        user.roles.append(default_role)
        await db.commit()
        await db.refresh(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        roles=[role.name for role in user.roles],
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Login and get access token.

    Args:
        form_data: OAuth2 password form data
        db: Database session

    Returns:
        Access and refresh tokens
    """
    # Get user
    query = select(User).where(User.username == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # Check if user exists and password is correct
    if not user or not verify_password(form_data.password, user.password_hash):
        # Increment failed login attempts
        if user:
            user.failed_login_attempts += 1

            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                from datetime import timedelta
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)

            await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Check if account is locked
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked due to too many failed login attempts. Please try again later.",
        )

    # Reset failed login attempts
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    await db.commit()

    # Create tokens
    from app.core.config import settings

    access_token = create_access_token(
        subject=user.username,
        additional_claims={
            "user_id": user.id,
            "email": user.email,
            "is_superuser": user.is_superuser,
        },
    )
    refresh_token = create_refresh_token(subject=user.username)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    Args:
        token_data: Refresh token
        db: Database session

    Returns:
        New access and refresh tokens
    """
    try:
        payload = decode_token(token_data.refresh_token)
        username: str = payload.get("sub")
        token_type: str = payload.get("type")

        if username is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Get user
    query = select(User).where(
        and_(User.username == username, User.is_active == True)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Create new tokens
    from app.core.config import settings

    access_token = create_access_token(
        subject=user.username,
        additional_claims={
            "user_id": user.id,
            "email": user.email,
            "is_superuser": user.is_superuser,
        },
    )
    new_refresh_token = create_refresh_token(subject=user.username)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
):
    """
    Logout current user.

    Note: With JWT, we can't truly invalidate the token server-side.
    The client should discard the token. For more security, implement
    a token blacklist using Redis.

    Args:
        current_user: Current authenticated user
    """
    # In a production system, you might want to:
    # 1. Add the token to a blacklist in Redis
    # 2. Track user sessions and invalidate them
    # For now, we just return success and let the client discard the token

    # Invalidate user's cache
    await cache_manager.delete_pattern(f"user:{current_user.id}:*")

    return None


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user details
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        roles=[role.name for role in current_user.roles],
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[EmailStr] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user information.

    Args:
        first_name: New first name
        last_name: New last name
        email: New email
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated user
    """
    # Check if email is already taken by another user
    if email and email != current_user.email:
        email_query = select(User).where(
            and_(User.email == email, User.id != current_user.id)
        )
        email_result = await db.execute(email_query)
        existing_email = email_result.scalar_one_or_none()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )

        current_user.email = email

    if first_name is not None:
        current_user.first_name = first_name

    if last_name is not None:
        current_user.last_name = last_name

    await db.commit()
    await db.refresh(current_user)

    # Invalidate cache
    await cache_manager.delete_pattern(f"user:{current_user.id}:*")

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        roles=[role.name for role in current_user.roles],
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change current user's password.

    Args:
        password_data: Current and new password
        current_user: Current authenticated user
        db: Database session
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )

    # Update password
    current_user.password_hash = hash_password(password_data.new_password)
    await db.commit()

    # Invalidate all caches for this user
    await cache_manager.delete_pattern(f"user:{current_user.id}:*")

    return None
