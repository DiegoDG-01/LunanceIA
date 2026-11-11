from datetime import datetime
from typing import cast

from application.auth.config import EmailAuthConfig
from application.auth.emails import VERIFY_EMAIL_PATH, app_link, email_verification
from application.interfaces.email import OutgoingEmail
from domain.entities.auth.pending_signup import EmailVerificationToken, PendingSignup
from domain.repositories.auth.pending_signup_repository import PendingSignupRepository
from shared.utils.tokens import generate_token, hash_token


async def issue_verification_email(
    repository: PendingSignupRepository,
    signup: PendingSignup,
    config: EmailAuthConfig,
    now: datetime,
) -> OutgoingEmail:
    """Un enlace más para el registro y el correo que lo lleva. Solo se guarda el hash; el
    enlace no dura más que el propio registro."""
    token = generate_token()
    expires_at = min(now + config.email_verification_ttl, signup.expires_at)
    await repository.add_token(
        EmailVerificationToken(
            token_hash=hash_token(token),
            pending_signup_id=cast(int, signup.id),
            created_at=now,
            expires_at=expires_at,
        )
    )
    return email_verification(
        to=signup.email,
        username=signup.username,
        link=app_link(config.link_base_url, VERIFY_EMAIL_PATH, token),
        ttl=expires_at - now,
    )
