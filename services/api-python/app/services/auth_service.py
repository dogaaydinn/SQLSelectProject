"""
Authentication Service Layer
Business logic for user authentication and authorization
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.repositories.user_repository import UserRepository, RoleRepository
from app.core.security import hash_password, verify_password, create_access_token
from app.utils.cache import cache_manager
from app.core.logging import logger
from app.models.user import User


class AuthService:
    """
    Service layer for authentication and authorization business logic.
    Handles user management, login, and security features.
    """

    # Security constants
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30

    def __init__(
        self,
        db: AsyncSession,
        user_repo: Optional[UserRepository] = None,
        role_repo: Optional[RoleRepository] = None,
    ):
        """
        Initialize service with database session and repositories.

        Args:
            db: Database session
            user_repo: User repository (optional)
            role_repo: Role repository (optional)
        """
        self.db = db
        self.user_repo = user_repo or UserRepository(db)
        self.role_repo = role_repo or RoleRepository(db)

    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register new user.

        Args:
            username: Username
            email: Email address
            password: Plain text password
            first_name: First name (optional)
            last_name: Last name (optional)

        Returns:
            Created user data

        Raises:
            ValueError: If business rules violated
        """
        # Business rule: Username must be unique
        if await self.user_repo.username_exists(username):
            raise ValueError(f"Username '{username}' already exists")

        # Business rule: Email must be unique
        if await self.user_repo.email_exists(email):
            raise ValueError(f"Email '{email}' already registered")

        # Business rule: Password must meet complexity requirements
        self._validate_password_strength(password)

        try:
            # Hash password
            password_hash = hash_password(password)

            # Create user
            user_data = {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "first_name": first_name,
                "last_name": last_name,
                "is_active": True,
                "is_superuser": False,
                "failed_login_attempts": 0,
            }

            user = await self.user_repo.create(user_data)
            await self.db.commit()

            logger.info(f"Registered new user: {username} ({email})")

            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
            }

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to register user: {e}")
            raise ValueError("Failed to register user due to data constraint violation")

    async def authenticate_user(
        self,
        username: str,
        password: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with username and password.

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            User data with access token, or None if authentication failed

        Raises:
            ValueError: If account is locked
        """
        # Try to find user by username or email
        user = await self.user_repo.get_by_username(username)
        if not user:
            user = await self.user_repo.get_by_email(username)

        if not user:
            logger.warning(f"Login attempt for non-existent user: {username}")
            return None

        # Check if account is locked
        if user.is_locked:
            raise ValueError(
                f"Account locked until {user.locked_until.isoformat()}. "
                "Please try again later."
            )

        # Check if account is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {username}")
            return None

        # Verify password
        if not verify_password(password, user.password_hash):
            # Increment failed login attempts
            await self.user_repo.increment_failed_login(user.id)

            # Lock account if too many failed attempts
            if user.failed_login_attempts + 1 >= self.MAX_FAILED_ATTEMPTS:
                await self.user_repo.lock_account(
                    user.id,
                    lock_duration_minutes=self.LOCKOUT_DURATION_MINUTES,
                )
                await self.db.commit()

                logger.warning(
                    f"Account locked for user {username} due to {self.MAX_FAILED_ATTEMPTS} "
                    "failed login attempts"
                )
                raise ValueError(
                    f"Account locked due to too many failed login attempts. "
                    f"Locked for {self.LOCKOUT_DURATION_MINUTES} minutes."
                )

            await self.db.commit()
            logger.warning(
                f"Failed login attempt for user {username} "
                f"({user.failed_login_attempts + 1} attempts)"
            )
            return None

        # Successful login - reset failed attempts and update last login
        await self.user_repo.reset_failed_login(user.id)
        await self.user_repo.update_last_login(user.id)
        await self.db.commit()

        # Generate access token
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "is_superuser": user.is_superuser,
            "roles": [role.name for role in user.roles if role.is_active],
        }
        access_token = create_access_token(token_data)

        logger.info(f"Successful login for user: {username}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_superuser": user.is_superuser,
                "roles": [role.name for role in user.roles if role.is_active],
            },
        }

    async def get_user_by_id(
        self,
        user_id: int,
        include_roles: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.

        Args:
            user_id: User ID
            include_roles: Include user roles

        Returns:
            User data or None
        """
        if include_roles:
            user = await self.user_repo.get_with_roles(user_id)
        else:
            user = await self.user_repo.get_by_id(user_id)

        if not user:
            return None

        return self._user_to_dict(user, include_roles=include_roles)

    async def update_user_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> bool:
        """
        Update user password.

        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password

        Returns:
            True if successful

        Raises:
            ValueError: If validation fails
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")

        # Validate new password strength
        self._validate_password_strength(new_password)

        # Business rule: New password cannot be same as current
        if current_password == new_password:
            raise ValueError("New password must be different from current password")

        # Hash and update password
        new_password_hash = hash_password(new_password)
        await self.user_repo.update(
            user_id,
            {"password_hash": new_password_hash},
            id_field="id",
        )
        await self.db.commit()

        logger.info(f"Password updated for user ID: {user_id}")

        return True

    async def assign_role_to_user(
        self,
        user_id: int,
        role_name: str,
    ) -> bool:
        """
        Assign role to user.

        Args:
            user_id: User ID
            role_name: Role name

        Returns:
            True if successful

        Raises:
            ValueError: If user or role not found
        """
        user = await self.user_repo.get_with_roles(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        role = await self.role_repo.get_by_name(role_name)
        if not role:
            raise ValueError(f"Role '{role_name}' not found")

        # Check if user already has this role
        if user.has_role(role_name):
            logger.info(f"User {user_id} already has role '{role_name}'")
            return True

        # Add role to user via UserRole table
        from app.models.user import UserRole

        user_role = UserRole(user_id=user_id, role_id=role.id)
        self.db.add(user_role)
        await self.db.commit()

        logger.info(f"Assigned role '{role_name}' to user {user_id}")

        return True

    async def check_user_permission(
        self,
        user_id: int,
        permission: str,
    ) -> bool:
        """
        Check if user has specific permission.

        Args:
            user_id: User ID
            permission: Permission string

        Returns:
            True if user has permission
        """
        user = await self.user_repo.get_with_roles(user_id)
        if not user:
            return False

        return user.has_permission(permission)

    async def get_users_by_role(
        self,
        role_name: str,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get all users with a specific role.

        Args:
            role_name: Role name
            active_only: Only include active users
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of users
        """
        users = await self.user_repo.get_users_by_role(
            role_name=role_name,
            active_only=active_only,
            skip=skip,
            limit=limit,
        )

        return [self._user_to_dict(user, include_roles=True) for user in users]

    async def get_locked_users(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get all currently locked users.

        Args:
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of locked users
        """
        users = await self.user_repo.get_locked_users(skip=skip, limit=limit)
        return [self._user_to_dict(user) for user in users]

    async def unlock_user_account(
        self,
        user_id: int,
    ) -> bool:
        """
        Manually unlock user account.

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        user = await self.user_repo.unlock_account(user_id)

        if user:
            await self.db.commit()
            logger.info(f"Unlocked user account: {user_id}")
            return True

        return False

    # ============================================
    # ROLE MANAGEMENT
    # ============================================

    async def create_role(
        self,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create new role.

        Args:
            name: Role name
            description: Role description
            permissions: List of permission strings

        Returns:
            Created role

        Raises:
            ValueError: If role name already exists
        """
        if await self.role_repo.role_name_exists(name):
            raise ValueError(f"Role '{name}' already exists")

        role_data = {
            "name": name,
            "description": description,
            "permissions": permissions or [],
            "is_active": True,
        }

        role = await self.role_repo.create(role_data)
        await self.db.commit()

        logger.info(f"Created role: {name}")

        return {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "permissions": role.permissions,
        }

    async def get_all_roles(self) -> List[Dict[str, Any]]:
        """
        Get all active roles.

        Returns:
            List of roles
        """
        roles = await self.role_repo.get_active_roles()
        return [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "permissions": role.permissions,
            }
            for role in roles
        ]

    # ============================================
    # PRIVATE HELPER METHODS
    # ============================================

    def _validate_password_strength(self, password: str) -> None:
        """
        Validate password meets strength requirements.

        Args:
            password: Password to validate

        Raises:
            ValueError: If password doesn't meet requirements
        """
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in password):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one number")

    def _user_to_dict(
        self,
        user: User,
        include_roles: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert user model to dictionary.

        Args:
            user: User model instance
            include_roles: Include roles and permissions

        Returns:
            User dictionary
        """
        data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "is_locked": user.is_locked,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

        if include_roles:
            data["roles"] = [
                {
                    "id": role.id,
                    "name": role.name,
                    "permissions": role.permissions,
                }
                for role in user.roles
                if role.is_active
            ]

        return data
