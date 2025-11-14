"""
Unit Tests for Security Utilities
Tests password hashing, JWT tokens, and authentication functions
"""

from datetime import timedelta
import pytest
from jose import jwt, JWTError

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_api_key,
    verify_api_key,
)


# ==========================================
# Password Hashing Tests
# ==========================================

@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash prefix

    def test_verify_password_success(self):
        """Test successful password verification."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_failure(self):
        """Test failed password verification."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "testpassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


# ==========================================
# JWT Token Tests
# ==========================================

@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Test creating an access token."""
        username = "testuser"
        token = create_access_token(subject=username)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_claims(self):
        """Test creating access token with additional claims."""
        username = "testuser"
        additional_claims = {
            "user_id": 123,
            "email": "test@example.com",
        }

        token = create_access_token(
            subject=username,
            additional_claims=additional_claims,
        )

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        assert payload["sub"] == username
        assert payload["user_id"] == 123
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_create_access_token_with_custom_expiration(self):
        """Test creating access token with custom expiration."""
        username = "testuser"
        expires_delta = timedelta(hours=2)

        token = create_access_token(
            subject=username,
            expires_delta=expires_delta,
        )

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        assert payload["sub"] == username
        # Expiration should be in the future
        assert "exp" in payload

    def test_create_refresh_token(self):
        """Test creating a refresh token."""
        username = "testuser"
        token = create_refresh_token(subject=username)

        assert token is not None
        assert isinstance(token, str)

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        assert payload["sub"] == username
        assert payload["type"] == "refresh"

    def test_decode_token_success(self):
        """Test successfully decoding a valid token."""
        username = "testuser"
        token = create_access_token(subject=username)

        payload = decode_token(token)

        assert payload["sub"] == username
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_token_invalid(self):
        """Test decoding an invalid token raises exception."""
        invalid_token = "invalid.token.here"

        with pytest.raises(Exception):  # Will raise HTTPException
            decode_token(invalid_token)

    def test_decode_token_expired(self):
        """Test decoding an expired token raises exception."""
        username = "testuser"
        # Create token with negative expiration (already expired)
        token = create_access_token(
            subject=username,
            expires_delta=timedelta(seconds=-10),
        )

        with pytest.raises(Exception):  # Will raise HTTPException for expired token
            decode_token(token)

    def test_token_contains_required_fields(self):
        """Test that token contains all required fields."""
        username = "testuser"
        token = create_access_token(subject=username)

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Check required fields
        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload

        assert payload["sub"] == username
        assert payload["type"] == "access"


# ==========================================
# API Key Hashing Tests
# ==========================================

@pytest.mark.unit
class TestAPIKeyHashing:
    """Test API key hashing functionality."""

    def test_hash_api_key(self):
        """Test API key hashing."""
        api_key = "test_api_key_12345"
        hashed = hash_api_key(api_key)

        assert hashed != api_key
        assert len(hashed) > 0

    def test_verify_api_key_success(self):
        """Test successful API key verification."""
        api_key = "test_api_key_12345"
        hashed = hash_api_key(api_key)

        assert verify_api_key(api_key, hashed) is True

    def test_verify_api_key_failure(self):
        """Test failed API key verification."""
        api_key = "test_api_key_12345"
        wrong_key = "wrong_api_key"
        hashed = hash_api_key(api_key)

        assert verify_api_key(wrong_key, hashed) is False


# ==========================================
# Token Validation Tests
# ==========================================

@pytest.mark.unit
class TestTokenValidation:
    """Test token validation logic."""

    def test_access_token_vs_refresh_token(self):
        """Test that access and refresh tokens have different types."""
        username = "testuser"

        access_token = create_access_token(subject=username)
        refresh_token = create_refresh_token(subject=username)

        access_payload = jwt.decode(
            access_token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        refresh_payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"

    def test_token_subject_integrity(self):
        """Test that token subject is preserved."""
        subjects = ["user1", "user2@example.com", "admin"]

        for subject in subjects:
            token = create_access_token(subject=subject)
            payload = decode_token(token)

            assert payload["sub"] == str(subject)

    def test_token_immutability(self):
        """Test that tokens cannot be tampered with."""
        username = "testuser"
        token = create_access_token(subject=username)

        # Tamper with the token
        tampered_token = token[:-10] + "tampered"

        with pytest.raises(Exception):
            decode_token(tampered_token)
