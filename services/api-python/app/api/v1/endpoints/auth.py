"""
Authentication Endpoints
Handles login, registration, token management
"""

from datetime import datetime, timedelta
from typing import List
import secrets
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    PasswordHasher,
    JWTHandler,
    get_current_user,
    get_current_superuser,
)
from app.models.user import User, Role, UserRole, APIKey
from app.schemas.auth import (
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
    RoleCreate,
    RoleResponse,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyListResponse,
    PasswordChange,
)
from app.core.logging import logger

router = APIRouter()


# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """
    Register new user.

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        Created user information
    """
    # Check if username exists
    query = select(User).where(User.username == user_data.username)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Check if email exists
    query = select(User).where(User.email == user_data.email)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=PasswordHasher.get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"User registered: {user.username}")

    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    User login with username and password.

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
    if not user or not PasswordHasher.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Account is locked until {user.locked_until}",
        )

    # Reset failed login attempts
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    await db.commit()

    # Create tokens
    access_token = JWTHandler.create_access_token(data={"sub": user.id})
    refresh_token = JWTHandler.create_refresh_token(data={"sub": user.id})

    logger.info(f"User logged in: {user.username}")

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    Args:
        refresh_token: JWT refresh token
        db: Database session

    Returns:
        New access and refresh tokens
    """
    try:
        payload = JWTHandler.decode_token(refresh_token)

        # Verify token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = payload.get("sub")

        # Get user
        query = select(User).where(User.id == user_id).where(User.is_active == True)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # Create new tokens
        new_access_token = JWTHandler.create_access_token(data={"sub": user.id})
        new_refresh_token = JWTHandler.create_refresh_token(data={"sub": user.id})

        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=3600,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current authenticated user information.

    Args:
        current_user: Current user from token
        db: Database session

    Returns:
        User information with roles
    """
    # Get user with roles
    query = select(User).where(User.id == current_user["id"])
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get user roles
    query = (
        select(Role)
        .join(UserRole)
        .where(UserRole.user_id == user.id)
        .where(Role.is_active == True)
    )
    result = await db.execute(query)
    roles = result.scalars().all()

    user_response = UserResponse.model_validate(user)
    user_response.roles = [role.name for role in roles]

    return user_response


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user information.

    Args:
        user_data: Updated user data
        current_user: Current user from token
        db: Database session

    Returns:
        Updated user information
    """
    query = select(User).where(User.id == current_user["id"])
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)

    if "password" in update_data:
        update_data["password_hash"] = PasswordHasher.get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change current user password.

    Args:
        password_data: Old and new passwords
        current_user: Current user from token
        db: Database session

    Returns:
        Success message
    """
    query = select(User).where(User.id == current_user["id"])
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify old password
    if not PasswordHasher.verify_password(password_data.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password",
        )

    # Update password
    user.password_hash = PasswordHasher.get_password_hash(password_data.new_password)
    await db.commit()

    logger.info(f"Password changed for user: {user.username}")

    return {"message": "Password changed successfully"}


# ============================================
# API KEY MANAGEMENT
# ============================================

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create new API key for current user.

    Args:
        key_data: API key creation data
        current_user: Current user from token
        db: Database session

    Returns:
        Created API key (key is only shown once!)
    """
    # Generate random API key
    api_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Calculate expiration
    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)

    # Create API key record
    api_key_obj = APIKey(
        key_hash=key_hash,
        user_id=current_user["id"],
        name=key_data.name,
        scopes=key_data.scopes,
        expires_at=expires_at,
    )

    db.add(api_key_obj)
    await db.commit()
    await db.refresh(api_key_obj)

    logger.info(f"API key created: {key_data.name} for user {current_user['username']}")

    response = APIKeyResponse.model_validate(api_key_obj)
    response.key = api_key  # Return actual key (only time it's shown!)

    return response


@router.get("/api-keys", response_model=List[APIKeyListResponse])
async def list_api_keys(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all API keys for current user.

    Args:
        current_user: Current user from token
        db: Database session

    Returns:
        List of API keys (without actual keys)
    """
    query = select(APIKey).where(APIKey.user_id == current_user["id"])
    result = await db.execute(query)
    api_keys = result.scalars().all()

    return [APIKeyListResponse.model_validate(key) for key in api_keys]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete API key.

    Args:
        key_id: API key ID
        current_user: Current user from token
        db: Database session
    """
    query = (
        select(APIKey)
        .where(APIKey.id == key_id)
        .where(APIKey.user_id == current_user["id"])
    )
    result = await db.execute(query)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await db.delete(api_key)
    await db.commit()

    logger.info(f"API key deleted: {api_key.name}")

    return None


# ============================================
# ROLE MANAGEMENT (Superuser only)
# ============================================

@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: dict = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    Create new role (superuser only).

    Args:
        role_data: Role creation data
        current_user: Current superuser
        db: Database session

    Returns:
        Created role
    """
    # Check if role exists
    query = select(Role).where(Role.name == role_data.name)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already exists",
        )

    # Create role
    role = Role(**role_data.model_dump())
    db.add(role)
    await db.commit()
    await db.refresh(role)

    logger.info(f"Role created: {role.name}")

    return RoleResponse.model_validate(role)


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all roles.

    Args:
        current_user: Current user
        db: Database session

    Returns:
        List of roles
    """
    query = select(Role).where(Role.is_active == True)
    result = await db.execute(query)
    roles = result.scalars().all()

    return [RoleResponse.model_validate(role) for role in roles]
