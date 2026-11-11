from dataclasses import replace
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from application.auth.commands.apple_notifications import (
    AppleNotificationCommand,
    AppleNotificationHandler,
)
from application.auth.commands.change_password import (
    ChangePasswordCommand,
    ChangePasswordHandler,
)
from application.auth.commands.change_username import (
    ChangeUsernameCommand,
    ChangeUsernameHandler,
)
from application.auth.commands.link_provider import (
    LinkProviderCommand,
    LinkProviderHandler,
    UnlinkProviderCommand,
    UnlinkProviderHandler,
)
from application.auth.commands.login import LoginCommand, LoginHandler
from application.auth.commands.logout import LogoutCommand, LogoutHandler
from application.auth.commands.password_reset import (
    RequestPasswordResetCommand,
    RequestPasswordResetHandler,
    ResetPasswordCommand,
    ResetPasswordHandler,
)
from application.auth.commands.provider_sign_in import (
    ProviderSignInCommand,
    ProviderSignInHandler,
    ProviderSignInResult,
)
from application.auth.commands.refresh_session import (
    RefreshSessionCommand,
    RefreshSessionHandler,
)
from application.auth.commands.register import RegisterCommand, RegisterHandler
from application.auth.commands.revoke_session import (
    RevokeSessionCommand,
    RevokeSessionHandler,
)
from application.auth.commands.verify_email import (
    ResendVerificationCommand,
    ResendVerificationHandler,
    VerifyEmailCommand,
    VerifyEmailHandler,
)
from application.auth.dto import ClientContext, IssuedSession
from application.auth.queries.list_sessions import (
    ListSessionsHandler,
    ListSessionsQuery,
)
from application.interfaces.identity_providers import IdentityProvider
from domain.entities.auth.session import Platform
from domain.entities.users.user import User
from infrastructure.cache.redis import claim_once
from infrastructure.config.settings import settings
from infrastructure.rate_limiting.client_ip import ip_identity
from infrastructure.rate_limiting.limiters import (
    RateLimitRule,
    enforce_rate_limit,
    limiter_5_per_hour,
    limiter_5_per_minute,
    limiter_10_per_minute,
    limiter_20_per_minute,
    limiter_30_per_minute,
    limiter_100_per_minute,
    limiter_password_reset_emails,
    limiter_signup_emails,
)
from presentation.dependencies import (
    get_change_password_handler,
    get_list_sessions_handler,
    get_login_handler,
    get_logout_handler,
    get_refresh_session_handler,
    get_register_handler,
    get_request_password_reset_handler,
    get_resend_verification_handler,
    get_reset_password_handler,
    get_revoke_session_handler,
    get_verify_email_handler,
)
from presentation.dependencies.auth_deps import (
    AccessContext,
    get_access_context,
    get_current_active_user,
)
from presentation.dependencies.client_deps import (
    get_client_context,
    get_device_context,
)
from presentation.dependencies.identity_deps import (
    get_apple_notification_handler,
    get_change_username_handler,
    get_link_provider_handler,
    get_provider_sign_in_handler,
    get_unlink_provider_handler,
)
from presentation.schemas.requests.auth import (
    AppleNotificationRequest,
    AppleSignInRequest,
    ChangePasswordRequest,
    EmailRequest,
    GoogleSignInRequest,
    LinkAppleRequest,
    LinkGoogleRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateMeRequest,
    VerifyEmailRequest,
)
from presentation.schemas.responses.auth import (
    LoginMethodsResponse,
    LogoutResponse,
    MessageResponse,
    ProviderTokenResponse,
    SessionResponse,
    TokenResponse,
    UserInfoResponse,
    VerifyEmailResponse,
)
from shared.utils.emails import email_digest
from shared.utils.time import utc_now

router = APIRouter()

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v2/auth"
# Un rate limit cortando el login se audita una vez por IP y minuto, no en cada intento.
THROTTLED_AUDIT_WINDOW_SECONDS = 60

# Las rutas públicas de cuenta responden lo mismo exista o no el correo (anti-enumeración).
SIGNUP_ACCEPTED_MESSAGE = (
    "Si el correo es válido, te enviamos un enlace para confirmar tu cuenta. "
    "Revisa tu bandeja de entrada y la carpeta de spam."
)
RESEND_ACCEPTED_MESSAGE = (
    "Si hay un registro pendiente con ese correo, te enviamos un enlace nuevo."
)
EMAIL_VERIFIED_MESSAGE = "Correo confirmado. Ya puedes iniciar sesión."

# Sin Idempotency-Key en estas rutas (fase 4): no mueven dinero ni duplican nada al repetirse.
# Repetir el registro sustituye el registro pendiente del mismo correo; cada enlace (verificar,
# restablecer) sirve una sola vez, y los reenvíos están limitados por buzón.


def _set_refresh_cookie(response: Response, issued: IssuedSession) -> None:
    max_age = round((issued.session.expires_at - utc_now()).total_seconds())
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=issued.refresh_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        max_age=max(max_age, 0),
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        path=REFRESH_COOKIE_PATH,
    )


def _token_response(response: Response, issued: IssuedSession) -> TokenResponse:
    """Web: el refresh va en la cookie httpOnly. ios/android: en el body."""
    token = TokenResponse(
        access_token=issued.access_token,
        token_type=issued.token_type,
        expires_in=issued.expires_in,
    )
    if issued.session.platform is Platform.WEB:
        _set_refresh_cookie(response, issued)
    else:
        token.refresh_token = issued.refresh_token
    return token


def _incoming_refresh_token(
    request: Request, context: ClientContext, body_token: str | None
) -> str:
    token = (
        request.cookies.get(REFRESH_COOKIE)
        if context.platform is Platform.WEB
        else body_token
    )
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token not found")
    return token


async def _limit_mailbox(
    request: Request, rule: RateLimitRule, purpose: str, email: str
) -> None:
    """Límite por buzón, aparte del de la IP. Fail-closed: sin Redis, 503."""
    await enforce_rate_limit(
        rule,
        request,
        key=f"mailbox:{purpose}:{email_digest(email)}",
        fail_closed=True,
    )


@router.post(
    "/register",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MessageResponse,
)
async def register(
    request: Request,
    register_request: RegisterRequest,
    context: ClientContext = Depends(get_client_context),
    handler: RegisterHandler = Depends(get_register_handler),
):
    """Guarda el registro y manda el enlace de verificación. Siempre 202 (salvo username
    ocupado, 409): la respuesta no revela si el correo ya tiene cuenta."""
    await enforce_rate_limit(limiter_5_per_hour, request, fail_closed=True)
    await _limit_mailbox(
        request, limiter_signup_emails, "signup", register_request.email
    )
    await handler.handle(
        RegisterCommand(
            email=register_request.email,
            username=register_request.username,
            password=register_request.password,
            context=context,
        )
    )
    return MessageResponse(message=SIGNUP_ACCEPTED_MESSAGE)


@router.post("/email/verify", response_model=VerifyEmailResponse)
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    context: ClientContext = Depends(get_client_context),
    handler: VerifyEmailHandler = Depends(get_verify_email_handler),
):
    """Abre el enlace del correo: crea la cuenta ya verificada. No inicia sesión."""
    await enforce_rate_limit(limiter_10_per_minute, request, fail_closed=True)
    user = await handler.handle(VerifyEmailCommand(token=body.token, context=context))
    return VerifyEmailResponse(
        user_uuid=user.uuid,
        username=user.name,
        email=user.email or "",
        message=EMAIL_VERIFIED_MESSAGE,
    )


@router.post(
    "/email/verify/resend",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MessageResponse,
)
async def resend_verification(
    request: Request,
    body: EmailRequest,
    context: ClientContext = Depends(get_client_context),
    handler: ResendVerificationHandler = Depends(get_resend_verification_handler),
):
    """Otro enlace para un registro pendiente. Siempre 202."""
    await enforce_rate_limit(limiter_5_per_minute, request, fail_closed=True)
    await _limit_mailbox(request, limiter_signup_emails, "signup", body.email)
    await handler.handle(ResendVerificationCommand(email=body.email, context=context))
    return MessageResponse(message=RESEND_ACCEPTED_MESSAGE)


@router.post("/password/forgot", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(
    request: Request,
    body: EmailRequest,
    context: ClientContext = Depends(get_client_context),
    handler: RequestPasswordResetHandler = Depends(get_request_password_reset_handler),
):
    """Manda el enlace para elegir una contraseña nueva. Siempre 204, incluso al llegar al
    límite del buzón (entonces no se manda nada): la respuesta no revela si hay cuenta."""
    await enforce_rate_limit(limiter_5_per_minute, request, fail_closed=True)
    try:
        await _limit_mailbox(
            request, limiter_password_reset_emails, "password_reset", body.email
        )
    except HTTPException as exc:
        if exc.status_code != status.HTTP_429_TOO_MANY_REQUESTS:
            raise
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    await handler.handle(RequestPasswordResetCommand(email=body.email, context=context))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    context: ClientContext = Depends(get_client_context),
    handler: ResetPasswordHandler = Depends(get_reset_password_handler),
):
    """Cambia la contraseña con el enlace del correo y cierra todas las sesiones."""
    await enforce_rate_limit(limiter_10_per_minute, request, fail_closed=True)
    await handler.handle(
        ResetPasswordCommand(token=body.token, password=body.password, context=context)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password/change", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    auth: AccessContext = Depends(get_access_context),
    context: ClientContext = Depends(get_client_context),
    handler: ChangePasswordHandler = Depends(get_change_password_handler),
):
    """Cambia la contraseña (pide la actual) y cierra las demás sesiones; esta sigue."""
    user_id = cast(int, auth.user.id)
    await enforce_rate_limit(
        limiter_5_per_minute,
        request,
        key=f"user:{user_id}:{request.url.path}",
        fail_closed=True,
    )
    await handler.handle(
        ChangePasswordCommand(
            user_id=user_id,
            session_uuid=auth.session_uuid,
            current_password=body.current_password,
            new_password=body.new_password,
            context=context,
        )
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _user_info(user: User) -> UserInfoResponse:
    return UserInfoResponse(
        user_uuid=user.uuid,
        username=user.name,
        email=user.email,
        email_verified=user.email_verified,
        is_active=user.is_active,
        login_methods=user.login_methods,
    )


@router.get("/me", response_model=UserInfoResponse)
async def me(request: Request, current_user: User = Depends(get_current_active_user)):
    await enforce_rate_limit(limiter_100_per_minute, request)
    return _user_info(current_user)


@router.patch("/me", response_model=UserInfoResponse)
async def update_me(
    request: Request,
    body: UpdateMeRequest,
    auth: AccessContext = Depends(get_access_context),
    context: ClientContext = Depends(get_client_context),
    handler: ChangeUsernameHandler = Depends(get_change_username_handler),
):
    """Cambia el username (las cuentas de Google y Apple empiezan con uno generado)."""
    user_id = cast(int, auth.user.id)
    await enforce_rate_limit(
        limiter_5_per_minute, request, key=f"user:{user_id}:{request.url.path}"
    )
    user = await handler.handle(
        ChangeUsernameCommand(user_id=user_id, username=body.username, context=context)
    )
    return _user_info(user)


@router.post("/login", response_model=TokenResponse, response_model_exclude_none=True)
async def login(
    request: Request,
    response: Response,
    login_request: LoginRequest,
    context: ClientContext = Depends(get_device_context),
    handler: LoginHandler = Depends(get_login_handler),
):
    command = LoginCommand(
        email=login_request.email,
        password=login_request.password,
        context=replace(context, device_name=login_request.device_name),
    )
    try:
        await enforce_rate_limit(limiter_10_per_minute, request, fail_closed=True)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS and await claim_once(
            f"audit:login_throttled:{ip_identity(request)}",
            THROTTLED_AUDIT_WINDOW_SECONDS,
        ):
            await handler.record_throttled(command)
        raise

    issued = await handler.handle(command)
    return _token_response(response, issued)


@router.post("/refresh", response_model=TokenResponse, response_model_exclude_none=True)
async def refresh_token(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    context: ClientContext = Depends(get_device_context),
    handler: RefreshSessionHandler = Depends(get_refresh_session_handler),
):
    await enforce_rate_limit(limiter_20_per_minute, request)
    token = _incoming_refresh_token(
        request, context, body.refresh_token if body else None
    )

    issued = await handler.handle(
        RefreshSessionCommand(refresh_token=token, context=context)
    )
    return _token_response(response, issued)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    body: LogoutRequest | None = None,
    context: ClientContext = Depends(get_client_context),
    handler: LogoutHandler = Depends(get_logout_handler),
):
    await enforce_rate_limit(limiter_10_per_minute, request)
    body = body or LogoutRequest()
    token = _incoming_refresh_token(request, context, body.refresh_token)

    await handler.handle(
        LogoutCommand(
            refresh_token=token, all_devices=body.all_devices, context=context
        )
    )

    if context.platform is Platform.WEB:
        _clear_refresh_cookie(response)
    return LogoutResponse()


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    request: Request,
    auth: AccessContext = Depends(get_access_context),
    handler: ListSessionsHandler = Depends(get_list_sessions_handler),
):
    await enforce_rate_limit(limiter_30_per_minute, request)
    views = await handler.handle(
        ListSessionsQuery(
            user_id=cast(int, auth.user.id),
            current_session_uuid=auth.session_uuid,
        )
    )
    return [
        SessionResponse(
            uuid=view.session.uuid,
            platform=view.session.platform.value,
            device_name=view.session.device_name,
            client=view.session.client,
            created_at=view.session.created_at,
            last_seen_at=view.session.last_seen_at,
            last_ip=view.session.last_ip,
            is_current=view.is_current,
        )
        for view in views
    ]


@router.delete("/sessions/{session_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    request: Request,
    session_uuid: UUID,
    auth: AccessContext = Depends(get_access_context),
    context: ClientContext = Depends(get_client_context),
    handler: RevokeSessionHandler = Depends(get_revoke_session_handler),
):
    await enforce_rate_limit(limiter_20_per_minute, request)
    await handler.handle(
        RevokeSessionCommand(
            user_id=cast(int, auth.user.id),
            session_uuid=str(session_uuid),
            actor_session_uuid=auth.session_uuid,
            context=context,
        )
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Google y Apple ---
# Sin Idempotency-Key: cada ID token sirve una sola vez, así que un reintento con el mismo token
# responde 401 y la app pide otro al proveedor.


def _provider_token_response(
    response: Response, result: ProviderSignInResult
) -> ProviderTokenResponse:
    token = _token_response(response, result.issued)
    return ProviderTokenResponse(
        **token.model_dump(),
        account_created=result.account_created,
        provider_linked=result.provider_linked,
    )


async def _limit_provider_sign_in(request: Request) -> None:
    """Mismo límite que el login con contraseña. Fail-closed: sin Redis, 503."""
    await enforce_rate_limit(limiter_10_per_minute, request, fail_closed=True)


@router.post(
    "/google", response_model=ProviderTokenResponse, response_model_exclude_none=True
)
async def google_sign_in(
    request: Request,
    response: Response,
    body: GoogleSignInRequest,
    context: ClientContext = Depends(get_device_context),
    handler: ProviderSignInHandler = Depends(get_provider_sign_in_handler),
):
    """Entra o crea la cuenta con el ID token de Google. Una cuenta con el mismo correo solo
    se vincula sola si es un buzón de Gmail o del dominio de Google Workspace de la cuenta;
    si no, 409 AUTH_PROVIDER_LINK_REQUIRED."""
    await _limit_provider_sign_in(request)
    result = await handler.handle(
        ProviderSignInCommand(
            provider=IdentityProvider.GOOGLE,
            id_token=body.id_token,
            nonce=body.nonce,
            context=replace(context, device_name=body.device_name),
        )
    )
    return _provider_token_response(response, result)


@router.post(
    "/apple", response_model=ProviderTokenResponse, response_model_exclude_none=True
)
async def apple_sign_in(
    request: Request,
    response: Response,
    body: AppleSignInRequest,
    context: ClientContext = Depends(get_device_context),
    handler: ProviderSignInHandler = Depends(get_provider_sign_in_handler),
):
    """Entra o crea la cuenta con Sign in with Apple. Con `authorization_code` se guarda
    (cifrado) el refresh token de Apple para poder revocar el acceso al borrar la cuenta."""
    await _limit_provider_sign_in(request)
    result = await handler.handle(
        ProviderSignInCommand(
            provider=IdentityProvider.APPLE,
            id_token=body.id_token,
            nonce=body.nonce,
            authorization_code=body.authorization_code,
            name=body.name,
            context=replace(context, device_name=body.device_name),
        )
    )
    return _provider_token_response(response, result)


@router.post("/apple/notifications", status_code=status.HTTP_200_OK)
async def apple_notifications(
    request: Request,
    body: AppleNotificationRequest,
    handler: AppleNotificationHandler = Depends(get_apple_notification_handler),
):
    """Avisos servidor a servidor de Apple (Apple Developer › Identifiers › el App ID ›
    Sign in with Apple › Server-to-Server Notification Endpoint). Apple espera un 200."""
    await enforce_rate_limit(limiter_100_per_minute, request)
    await handler.handle(AppleNotificationCommand(payload=body.payload))
    return Response(status_code=status.HTTP_200_OK)


async def _limit_provider_change(request: Request, user_id: int) -> None:
    await enforce_rate_limit(
        limiter_5_per_minute,
        request,
        key=f"user:{user_id}:auth/providers",
        fail_closed=True,
    )


@router.post("/providers/google", response_model=LoginMethodsResponse)
async def link_google(
    request: Request,
    body: LinkGoogleRequest,
    auth: AccessContext = Depends(get_access_context),
    context: ClientContext = Depends(get_client_context),
    handler: LinkProviderHandler = Depends(get_link_provider_handler),
):
    """Vincula una cuenta de Google a la cuenta con sesión iniciada (desde ajustes). Pide la
    contraseña actual o, sin contraseña, una sesión reciente (403 AUTH_REAUTH_REQUIRED)."""
    user_id = cast(int, auth.user.id)
    await _limit_provider_change(request, user_id)
    user = await handler.handle(
        LinkProviderCommand(
            user_id=user_id,
            session_uuid=auth.session_uuid,
            provider=IdentityProvider.GOOGLE,
            id_token=body.id_token,
            nonce=body.nonce,
            current_password=body.current_password,
            context=context,
        )
    )
    return LoginMethodsResponse(login_methods=user.login_methods)


@router.post("/providers/apple", response_model=LoginMethodsResponse)
async def link_apple(
    request: Request,
    body: LinkAppleRequest,
    auth: AccessContext = Depends(get_access_context),
    context: ClientContext = Depends(get_client_context),
    handler: LinkProviderHandler = Depends(get_link_provider_handler),
):
    """Vincula una cuenta de Apple a la cuenta con sesión iniciada (desde ajustes). Pide la
    contraseña actual o, sin contraseña, una sesión reciente (403 AUTH_REAUTH_REQUIRED)."""
    user_id = cast(int, auth.user.id)
    await _limit_provider_change(request, user_id)
    user = await handler.handle(
        LinkProviderCommand(
            user_id=user_id,
            session_uuid=auth.session_uuid,
            provider=IdentityProvider.APPLE,
            id_token=body.id_token,
            nonce=body.nonce,
            authorization_code=body.authorization_code,
            current_password=body.current_password,
            context=context,
        )
    )
    return LoginMethodsResponse(login_methods=user.login_methods)


@router.delete("/providers/{provider}", response_model=LoginMethodsResponse)
async def unlink_provider(
    request: Request,
    provider: IdentityProvider,
    auth: AccessContext = Depends(get_access_context),
    context: ClientContext = Depends(get_client_context),
    handler: UnlinkProviderHandler = Depends(get_unlink_provider_handler),
):
    """Desvincula Google o Apple. 409 AUTH_LAST_LOGIN_METHOD si es la única forma de entrar."""
    user_id = cast(int, auth.user.id)
    await _limit_provider_change(request, user_id)
    user = await handler.handle(
        UnlinkProviderCommand(
            user_id=user_id,
            session_uuid=auth.session_uuid,
            provider=provider,
            context=context,
        )
    )
    return LoginMethodsResponse(login_methods=user.login_methods)
