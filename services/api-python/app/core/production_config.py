"""
Production-Ready Configuration Enhancements
Security hardening and production best practices
"""

import secrets
from typing import Optional
from pydantic import field_validator


class ProductionSecurityMixin:
    """
    Mixin for production security enhancements.

    This mixin provides:
    - Automatic secret key generation
    - Security header configurations
    - Rate limiting enhancements
    - CORS restriction enforcement
    """

    @staticmethod
    def generate_secret_key() -> str:
        """Generate a cryptographically secure secret key."""
        return secrets.token_urlsafe(64)

    @classmethod
    def validate_production_secrets(cls, values: dict) -> dict:
        """
        Validate that production secrets are properly set.

        Args:
            values: Configuration values

        Returns:
            Validated values

        Raises:
            ValueError: If production environment has insecure defaults
        """
        environment = values.get("ENVIRONMENT", "development")

        if environment == "production":
            # Check SECRET_KEY
            if values.get("SECRET_KEY") == "your-secret-key-change-in-production":
                raise ValueError(
                    "SECRET_KEY must be changed in production! "
                    "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
                )

            # Check JWT_SECRET
            if values.get("JWT_SECRET") == "your-jwt-secret-change-in-production":
                raise ValueError(
                    "JWT_SECRET must be changed in production! "
                    "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
                )

            # Enforce HTTPS in production
            if not values.get("FORCE_HTTPS", False):
                import warnings
                warnings.warn(
                    "FORCE_HTTPS should be enabled in production",
                    RuntimeWarning
                )

            # Restrict CORS origins
            cors_origins = values.get("CORS_ORIGINS", [])
            if "*" in cors_origins or "http://localhost" in str(cors_origins):
                raise ValueError(
                    "CORS_ORIGINS must be restricted in production. "
                    "Remove wildcard (*) and localhost origins."
                )

            # Enforce allowed hosts
            allowed_hosts = values.get("ALLOWED_HOSTS", [])
            if "*" in allowed_hosts:
                raise ValueError(
                    "ALLOWED_HOSTS must be restricted in production. "
                    "Remove wildcard (*)."
                )

            # Disable debug mode
            if values.get("DEBUG", False):
                raise ValueError("DEBUG must be False in production")

            # Disable API docs in production (optional, but recommended)
            if values.get("ENABLE_DOCS", True):
                import warnings
                warnings.warn(
                    "Consider disabling API docs in production (ENABLE_DOCS=False)",
                    RuntimeWarning
                )

        return values


# Security Headers for Production
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


# Production Rate Limits
PRODUCTION_RATE_LIMITS = {
    "default": "100/minute",
    "auth_login": "5/minute",
    "auth_register": "3/hour",
    "api_write": "30/minute",
    "api_read": "100/minute",
    "admin": "1000/minute",
}


# Production Database Pool Settings
PRODUCTION_DB_POOL = {
    "pool_size": 20,
    "max_overflow": 40,
    "pool_timeout": 30,
    "pool_recycle": 3600,  # Recycle connections after 1 hour
    "pool_pre_ping": True,  # Verify connections before using
    "echo": False,
    "echo_pool": False,
}


# Production Cache Settings
PRODUCTION_CACHE = {
    "ttl": 600,  # 10 minutes default
    "max_connections": 50,
    "socket_timeout": 5,
    "socket_connect_timeout": 5,
    "retry_on_timeout": True,
    "health_check_interval": 30,
}


# Production Logging Configuration
PRODUCTION_LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "/var/log/app/api.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json",
            "filename": "/var/log/app/error.log",
            "maxBytes": 10485760,
            "backupCount": 10,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file", "error_file"],
    },
}


# Health Check Configuration
HEALTH_CHECK_CONFIG = {
    "database": {
        "enabled": True,
        "timeout": 5,
        "critical": True,
    },
    "redis": {
        "enabled": True,
        "timeout": 3,
        "critical": False,  # Non-critical, app can run without cache
    },
    "external_services": {
        "enabled": True,
        "timeout": 10,
        "critical": False,
    },
}


# Monitoring and Observability
OBSERVABILITY_CONFIG = {
    "metrics": {
        "enabled": True,
        "endpoint": "/metrics",
        "include_in_schema": False,
    },
    "tracing": {
        "enabled": True,
        "sample_rate": 0.1,  # Sample 10% of requests
        "service_name": "employee-api",
    },
    "profiling": {
        "enabled": False,  # Only enable when debugging performance
        "endpoint": "/debug/profile",
    },
}
