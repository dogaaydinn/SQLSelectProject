"""
Integration Tests for Authentication Endpoints
Tests /auth/* endpoints for registration, login, token refresh, etc.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import hash_password


# ==========================================
# Registration Tests
# ==========================================

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.api
class TestUserRegistration:
    """Test user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_new_user(self, client: AsyncClient):
        """Test successful user registration."""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword123",
            "first_name": "New",
            "last_name": "User",
        }

        response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["is_active"] is True
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_username(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """Test registration with duplicate username fails."""
        user_data = {
            "username": test_user.username,
            "email": "different@example.com",
            "password": "password123",
        }

        response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """Test registration with duplicate email fails."""
        user_data = {
            "username": "differentuser",
            "email": test_user.email,
            "password": "password123",
        }

        response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email format fails."""
        user_data = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "password123",
        }

        response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        """Test registration with short password fails."""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "short",  # Less than 8 characters
        }

        response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 422  # Validation error


# ==========================================
# Login Tests
# ==========================================

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.api
class TestUserLogin:
    """Test user login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login."""
        login_data = {
            "username": "testuser",
            "password": "testpassword123",
        }

        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,  # OAuth2 uses form data
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """Test login with wrong password fails."""
        login_data = {
            "username": "testuser",
            "password": "wrongpassword",
        }

        response = await client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user fails."""
        login_data = {
            "username": "nonexistent",
            "password": "password123",
        }

        response = await client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test login with inactive user fails."""
        # Create inactive user
        user = User(
            username="inactive",
            email="inactive@example.com",
            password_hash=hash_password("password123"),
            is_active=False,
        )
        db_session.add(user)
        await db_session.commit()

        login_data = {
            "username": "inactive",
            "password": "password123",
        }

        response = await client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_failed_login_attempts(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test account locking after failed login attempts."""
        login_data = {
            "username": "testuser",
            "password": "wrongpassword",
        }

        # Make 5 failed attempts
        for _ in range(5):
            response = await client.post("/api/v1/auth/login", data=login_data)
            assert response.status_code == 401

        # 6th attempt should indicate account is locked
        response = await client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 403
        assert "locked" in response.json()["detail"].lower()


# ==========================================
# Token Refresh Tests
# ==========================================

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.api
class TestTokenRefresh:
    """Test token refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """Test successful token refresh."""
        # First login to get tokens
        login_data = {
            "username": "testuser",
            "password": "testpassword123",
        }
        login_response = await client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()

        # Refresh the token
        refresh_data = {"refresh_token": tokens["refresh_token"]}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New tokens should be different
        assert data["access_token"] != tokens["access_token"]

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        """Test refresh with invalid token fails."""
        refresh_data = {"refresh_token": "invalid.token.here"}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_access_token(
        self,
        client: AsyncClient,
        user_token: str,
    ):
        """Test refresh with access token instead of refresh token fails."""
        refresh_data = {"refresh_token": user_token}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 401


# ==========================================
# Current User Tests
# ==========================================

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.api
class TestCurrentUser:
    """Test current user endpoints."""

    @pytest.mark.asyncio
    async def test_get_current_user(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test getting current user information."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without authentication fails."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_current_user(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test updating current user information."""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@example.com",
        }

        response = await client.put(
            "/api/v1/auth/me",
            params=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["email"] == "updated@example.com"


# ==========================================
# Password Change Tests
# ==========================================

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.api
class TestPasswordChange:
    """Test password change endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test successful password change."""
        password_data = {
            "current_password": "testpassword123",
            "new_password": "newpassword123",
        }

        response = await client.post(
            "/api/v1/auth/change-password",
            json=password_data,
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify new password works
        login_data = {
            "username": "testuser",
            "password": "newpassword123",
        }
        login_response = await client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test password change with wrong current password fails."""
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123",
        }

        response = await client.post(
            "/api/v1/auth/change-password",
            json=password_data,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_change_password_unauthorized(self, client: AsyncClient):
        """Test password change without authentication fails."""
        password_data = {
            "current_password": "testpassword123",
            "new_password": "newpassword123",
        }

        response = await client.post(
            "/api/v1/auth/change-password",
            json=password_data,
        )

        assert response.status_code == 401


# ==========================================
# Logout Tests
# ==========================================

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.api
class TestLogout:
    """Test logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test successful logout."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_logout_unauthorized(self, client: AsyncClient):
        """Test logout without authentication fails."""
        response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 401
