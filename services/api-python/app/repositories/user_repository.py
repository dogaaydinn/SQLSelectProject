"""
User Repository
Domain-specific data access for User entity
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Role, ApiKey
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entity with domain-specific queries."""

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_username(
        self,
        username: str,
        include_roles: bool = True,
    ) -> Optional[User]:
        """
        Get user by username with optional role loading.

        Args:
            username: Username to search for
            include_roles: Load user roles and permissions

        Returns:
            User instance or None
        """
        query = select(User).where(User.username == username)

        if include_roles:
            query = query.options(
                selectinload(User.roles),
                selectinload(User.api_keys),
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(
        self,
        email: str,
        include_roles: bool = True,
    ) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: Email address to search for
            include_roles: Load user roles and permissions

        Returns:
            User instance or None
        """
        query = select(User).where(User.email == email)

        if include_roles:
            query = query.options(
                selectinload(User.roles),
                selectinload(User.api_keys),
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def search_users(
        self,
        search_term: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
        role_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """
        Search users with multiple criteria.

        Args:
            search_term: Search in username, email, first/last name
            is_active: Filter by active status
            is_superuser: Filter by superuser status
            role_name: Filter by role name
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of matching users
        """
        query = select(User)

        # Search in username, email, name
        if search_term:
            search_filter = or_(
                User.username.ilike(f"%{search_term}%"),
                User.email.ilike(f"%{search_term}%"),
                User.first_name.ilike(f"%{search_term}%"),
                User.last_name.ilike(f"%{search_term}%"),
            )
            query = query.where(search_filter)

        # Active status filter
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        # Superuser filter
        if is_superuser is not None:
            query = query.where(User.is_superuser == is_superuser)

        # Role filter (requires join)
        if role_name:
            from app.models.user import UserRole

            query = (
                query
                .join(UserRole, User.id == UserRole.user_id)
                .join(Role, UserRole.role_id == Role.id)
                .where(
                    and_(
                        Role.name == role_name,
                        Role.is_active == True,
                    )
                )
            )

        # Eager load relationships
        query = query.options(
            selectinload(User.roles),
            selectinload(User.api_keys),
        )

        # Pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_active_users(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """
        Get all active users.

        Args:
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of active users
        """
        query = (
            select(User)
            .where(User.is_active == True)
            .options(selectinload(User.roles))
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_with_roles(
        self,
        user_id: int,
    ) -> Optional[User]:
        """
        Get user with all roles and permissions eagerly loaded.

        Args:
            user_id: User ID

        Returns:
            User with roles loaded
        """
        query = (
            select(User)
            .options(
                selectinload(User.roles),
                selectinload(User.api_keys),
            )
            .where(User.id == user_id)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_users_by_role(
        self,
        role_name: str,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """
        Get all users with a specific role.

        Args:
            role_name: Role name to filter by
            active_only: Only include active users
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of users with the role
        """
        from app.models.user import UserRole

        query = (
            select(User)
            .join(UserRole, User.id == UserRole.user_id)
            .join(Role, UserRole.role_id == Role.id)
            .where(
                and_(
                    Role.name == role_name,
                    Role.is_active == True,
                )
            )
            .options(
                selectinload(User.roles),
                selectinload(User.api_keys),
            )
        )

        if active_only:
            query = query.where(User.is_active == True)

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def username_exists(
        self,
        username: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """
        Check if username is already in use.

        Args:
            username: Username to check
            exclude_id: Exclude this user ID (for updates)

        Returns:
            True if username exists, False otherwise
        """
        query = select(func.count()).select_from(User).where(
            User.username == username
        )

        if exclude_id:
            query = query.where(User.id != exclude_id)

        result = await self.db.execute(query)
        return result.scalar() > 0

    async def email_exists(
        self,
        email: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """
        Check if email is already in use.

        Args:
            email: Email to check
            exclude_id: Exclude this user ID (for updates)

        Returns:
            True if email exists, False otherwise
        """
        query = select(func.count()).select_from(User).where(
            User.email == email
        )

        if exclude_id:
            query = query.where(User.id != exclude_id)

        result = await self.db.execute(query)
        return result.scalar() > 0

    async def update_last_login(
        self,
        user_id: int,
    ) -> Optional[User]:
        """
        Update user's last login timestamp.

        Args:
            user_id: User ID

        Returns:
            Updated user or None
        """
        return await self.update(
            user_id,
            {"last_login": datetime.utcnow()},
            id_field="id",
        )

    async def increment_failed_login(
        self,
        user_id: int,
    ) -> Optional[User]:
        """
        Increment failed login attempts counter.

        Args:
            user_id: User ID

        Returns:
            Updated user or None
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        return await self.update(
            user_id,
            {"failed_login_attempts": user.failed_login_attempts + 1},
            id_field="id",
        )

    async def reset_failed_login(
        self,
        user_id: int,
    ) -> Optional[User]:
        """
        Reset failed login attempts counter.

        Args:
            user_id: User ID

        Returns:
            Updated user or None
        """
        return await self.update(
            user_id,
            {"failed_login_attempts": 0, "locked_until": None},
            id_field="id",
        )

    async def lock_account(
        self,
        user_id: int,
        lock_duration_minutes: int = 30,
    ) -> Optional[User]:
        """
        Lock user account for specified duration.

        Args:
            user_id: User ID
            lock_duration_minutes: Duration to lock account in minutes

        Returns:
            Updated user or None
        """
        locked_until = datetime.utcnow() + timedelta(minutes=lock_duration_minutes)

        return await self.update(
            user_id,
            {"locked_until": locked_until},
            id_field="id",
        )

    async def unlock_account(
        self,
        user_id: int,
    ) -> Optional[User]:
        """
        Unlock user account.

        Args:
            user_id: User ID

        Returns:
            Updated user or None
        """
        return await self.update(
            user_id,
            {"locked_until": None, "failed_login_attempts": 0},
            id_field="id",
        )

    async def get_locked_users(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """
        Get all currently locked users.

        Args:
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of locked users
        """
        query = (
            select(User)
            .where(
                and_(
                    User.locked_until.isnot(None),
                    User.locked_until > datetime.utcnow(),
                )
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_users_with_high_failed_logins(
        self,
        threshold: int = 3,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """
        Get users with high failed login attempts.

        Args:
            threshold: Minimum failed login attempts
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of users with high failed logins
        """
        query = (
            select(User)
            .where(User.failed_login_attempts >= threshold)
            .order_by(User.failed_login_attempts.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_status(self) -> Dict[str, int]:
        """
        Count users grouped by active status.

        Returns:
            Dictionary of status: count
        """
        query = (
            select(User.is_active, func.count(User.id))
            .group_by(User.is_active)
        )

        result = await self.db.execute(query)
        return {("active" if is_active else "inactive"): count for is_active, count in result.all()}

    async def get_superusers(
        self,
        active_only: bool = True,
    ) -> List[User]:
        """
        Get all superuser accounts.

        Args:
            active_only: Only include active superusers

        Returns:
            List of superuser accounts
        """
        query = select(User).where(User.is_superuser == True)

        if active_only:
            query = query.where(User.is_active == True)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_recently_active_users(
        self,
        days: int = 30,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """
        Get users active within last N days.

        Args:
            days: Number of days to look back
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of recently active users
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = (
            select(User)
            .where(
                and_(
                    User.last_login >= cutoff,
                    User.is_active == True,
                )
            )
            .order_by(User.last_login.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())


class RoleRepository(BaseRepository[Role]):
    """Repository for Role entity with domain-specific queries."""

    def __init__(self, db: AsyncSession):
        super().__init__(Role, db)

    async def get_by_name(
        self,
        name: str,
        include_users: bool = False,
    ) -> Optional[Role]:
        """
        Get role by name.

        Args:
            name: Role name
            include_users: Load users with this role

        Returns:
            Role instance or None
        """
        query = select(Role).where(Role.name == name)

        if include_users:
            query = query.options(selectinload(Role.users))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_roles(self) -> List[Role]:
        """
        Get all active roles.

        Returns:
            List of active roles
        """
        query = select(Role).where(Role.is_active == True)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def role_name_exists(
        self,
        name: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """
        Check if role name is already in use.

        Args:
            name: Role name to check
            exclude_id: Exclude this role ID (for updates)

        Returns:
            True if name exists, False otherwise
        """
        query = select(func.count()).select_from(Role).where(
            Role.name == name
        )

        if exclude_id:
            query = query.where(Role.id != exclude_id)

        result = await self.db.execute(query)
        return result.scalar() > 0

    async def add_permission(
        self,
        role_id: int,
        permission: str,
    ) -> Optional[Role]:
        """
        Add permission to role.

        Args:
            role_id: Role ID
            permission: Permission string to add

        Returns:
            Updated role or None
        """
        role = await self.get_by_id(role_id)
        if not role:
            return None

        if permission not in role.permissions:
            permissions = list(role.permissions) if role.permissions else []
            permissions.append(permission)

            return await self.update(
                role_id,
                {"permissions": permissions},
                id_field="id",
            )

        return role

    async def remove_permission(
        self,
        role_id: int,
        permission: str,
    ) -> Optional[Role]:
        """
        Remove permission from role.

        Args:
            role_id: Role ID
            permission: Permission string to remove

        Returns:
            Updated role or None
        """
        role = await self.get_by_id(role_id)
        if not role:
            return None

        if role.permissions and permission in role.permissions:
            permissions = list(role.permissions)
            permissions.remove(permission)

            return await self.update(
                role_id,
                {"permissions": permissions},
                id_field="id",
            )

        return role
