"""Servicios de autenticación construidos una vez a partir de `settings`."""

import hmac
from datetime import timedelta
from functools import lru_cache

from fastapi import Depends

from application.auth.config import AuthConfig, EmailAuthConfig
from application.auth.services.login_guard import LoginGuard
from application.interfaces.auth_service import (
    AccessTokenIssuer,
    PasswordHasher,
    SessionRevocationList,
)
from domain.entities.auth.session import SessionLifetime
from domain.repositories.auth.session_repository import SessionRepository
from infrastructure.cache.login_throttle import RedisLoginThrottle
from infrastructure.cache.redis import get_redis
from infrastructure.cache.session_revocations import PersistentSessionRevocations
from infrastructure.config.settings import settings
from infrastructure.security.jwt_tokens import EdDSATokenIssuer
from infrastructure.security.passwords import Argon2PasswordHasher
from presentation.dependencies.repositories import get_session_repository


@lru_cache
def get_token_issuer() -> AccessTokenIssuer:
    return EdDSATokenIssuer(
        private_key_pem=settings.JWT_PRIVATE_KEY.get_secret_value(),
        public_key_pem=settings.JWT_PUBLIC_KEY,
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
        ttl_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@lru_cache
def get_password_hasher() -> PasswordHasher:
    return Argon2PasswordHasher()


@lru_cache
def get_auth_config() -> AuthConfig:
    return AuthConfig(
        web_session=SessionLifetime(
            idle=timedelta(days=settings.SESSION_WEB_IDLE_DAYS),
            absolute=timedelta(days=settings.SESSION_WEB_ABSOLUTE_DAYS),
        ),
        mobile_session=SessionLifetime(
            idle=timedelta(days=settings.SESSION_MOBILE_IDLE_DAYS),
            absolute=timedelta(days=settings.SESSION_MOBILE_ABSOLUTE_DAYS),
        ),
        refresh_reuse_grace=timedelta(seconds=settings.REFRESH_REUSE_GRACE_SECONDS),
        # Se deriva una clave de uso único: el secreto del .env no se usa tal cual.
        refresh_rotation_key=hmac.digest(
            settings.REFRESH_ROTATION_KEY.get_secret_value().encode(),
            b"lunance:refresh-rotation-key:v1",
            "sha256",
        ),
    )


@lru_cache
def get_email_auth_config() -> EmailAuthConfig:
    return EmailAuthConfig(
        link_base_url=settings.email_link_base_url,
        email_verification_ttl=timedelta(hours=settings.EMAIL_VERIFICATION_TTL_HOURS),
        pending_signup_ttl=timedelta(days=settings.PENDING_SIGNUP_TTL_DAYS),
        password_reset_ttl=timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES),
    )


@lru_cache
def get_login_guard() -> LoginGuard:
    # Los throttles leen el cliente de Redis en cada uso (se abre en el lifespan).
    return LoginGuard(
        per_ip=RedisLoginThrottle(get_redis),
        per_account=RedisLoginThrottle.per_account(get_redis),
    )


def revocation_ttl_seconds() -> int:
    # Lo que puede seguir siendo válido un access token firmado, con el margen de reloj.
    return get_token_issuer().ttl_seconds + 60


def build_session_revocations(
    session_repository: SessionRepository,
) -> SessionRevocationList:
    return PersistentSessionRevocations(
        get_redis,
        ttl_seconds=revocation_ttl_seconds(),
        session_repository=session_repository,
    )


def get_session_revocations(
    session_repository: SessionRepository = Depends(get_session_repository),
) -> SessionRevocationList:
    return build_session_revocations(session_repository)
