"""Plantillas de los correos de cuenta (texto y HTML). Viven aquí y no en los proveedores:
cambiar de proveedor nunca toca un texto.

Los enlaces apuntan al frontend (`EMAIL_LINK_BASE_URL`), que lee el `token` de la URL y llama
a la API (`POST /auth/email/verify`, `POST /auth/password/reset`).
"""

from dataclasses import dataclass
from datetime import timedelta
from html import escape
from urllib.parse import urlencode

from application.interfaces.email import OutgoingEmail

APP_NAME = "Lunance"

VERIFY_EMAIL_PATH = "verify-email"
RESET_PASSWORD_PATH = "reset-password"
RESEND_VERIFICATION_PATH = "verify-email/resend"
FORGOT_PASSWORD_PATH = "forgot-password"
LOGIN_PATH = "login"


def app_link(base_url: str, path: str, token: str | None = None) -> str:
    """`https://lunance.app` + `verify-email` → `https://lunance.app/verify-email?token=…`."""
    link = f"{base_url.rstrip('/')}/{path}"
    return f"{link}?{urlencode({'token': token})}" if token else link


def describe_ttl(ttl: timedelta) -> str:
    """`24 horas`, `1 hora`, `30 minutos`: para el aviso de caducidad."""
    minutes = max(1, round(ttl.total_seconds() / 60))
    if minutes % (60 * 24) == 0:
        days = minutes // (60 * 24)
        return "1 día" if days == 1 else f"{days} días"
    if minutes % 60 == 0:
        hours = minutes // 60
        return "1 hora" if hours == 1 else f"{hours} horas"
    return "1 minuto" if minutes == 1 else f"{minutes} minutos"


@dataclass(frozen=True, slots=True)
class _Action:
    label: str
    url: str


def _render_html(
    *,
    title: str,
    greeting: str,
    paragraphs: list[str],
    action: _Action | None = None,
    notice: str | None = None,
) -> str:
    """HTML sencillo con estilos en línea (los clientes de correo ignoran las hojas de estilo).
    Todo el texto dinámico se escapa."""
    body = "".join(
        f'<p style="margin:0 0 16px;line-height:1.5">{escape(text)}</p>'
        for text in paragraphs
    )
    button = ""
    if action:
        url = escape(action.url, quote=True)
        button = (
            '<p style="margin:24px 0">'
            f'<a href="{url}" style="background:#4f46e5;color:#ffffff;padding:12px 20px;'
            'border-radius:6px;text-decoration:none;display:inline-block;font-weight:600">'
            f"{escape(action.label)}</a></p>"
            '<p style="margin:0 0 16px;font-size:13px;color:#555;line-height:1.5">'
            "Si el botón no funciona, copia este enlace en tu navegador:<br>"
            f'<a href="{url}" style="color:#4f46e5;word-break:break-all">{url}</a></p>'
        )
    footer = (
        f'<p style="margin:24px 0 0;font-size:13px;color:#555;line-height:1.5">'
        f"{escape(notice)}</p>"
        if notice
        else ""
    )
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        f"<title>{escape(title)}</title></head>"
        '<body style="margin:0;padding:24px;background:#f5f5f7;font-family:Arial,sans-serif;'
        'color:#1d1d1f">'
        '<div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:8px;'
        'padding:32px">'
        f'<h1 style="margin:0 0 24px;font-size:20px">{escape(title)}</h1>'
        f'<p style="margin:0 0 16px;line-height:1.5">{escape(greeting)}</p>'
        f"{body}{button}{footer}"
        f'<p style="margin:32px 0 0;font-size:12px;color:#888">{APP_NAME}</p>'
        "</div></body></html>"
    )


def _render_text(
    greeting: str,
    paragraphs: list[str],
    action: _Action | None = None,
    notice: str | None = None,
) -> str:
    parts = [greeting, *paragraphs]
    if action:
        parts.append(f"{action.label}: {action.url}")
    if notice:
        parts.append(notice)
    parts.append(f"— {APP_NAME}")
    return "\n\n".join(parts)


def _email(
    *,
    to: str,
    subject: str,
    title: str,
    greeting: str,
    paragraphs: list[str],
    tag: str,
    action: _Action | None = None,
    notice: str | None = None,
) -> OutgoingEmail:
    return OutgoingEmail(
        to=[to],
        subject=subject,
        text=_render_text(greeting, paragraphs, action, notice),
        html=_render_html(
            title=title,
            greeting=greeting,
            paragraphs=paragraphs,
            action=action,
            notice=notice,
        ),
        tag=tag,
    )


def email_verification(
    *, to: str, username: str, link: str, ttl: timedelta
) -> OutgoingEmail:
    return _email(
        to=to,
        subject=f"Confirma tu correo en {APP_NAME}",
        title="Confirma tu correo",
        greeting=f"Hola, {username}:",
        paragraphs=[
            (
                f"Pulsa el botón para confirmar tu correo y crear tu cuenta «{username}» "
                f"en {APP_NAME}."
            )
        ],
        action=_Action("Confirmar correo", link),
        notice=f"El enlace caduca en {describe_ttl(ttl)}. Si no te registraste en "
        f"{APP_NAME}, ignora este correo: no se creará ninguna cuenta.",
        tag="verify-email",
    )


def account_already_exists(
    *, to: str, login_link: str, forgot_link: str
) -> OutgoingEmail:
    """Alguien intentó registrarse con un correo que ya tiene cuenta. No se revela en la
    respuesta de la API: solo lo sabe quien lee el buzón."""
    return _email(
        to=to,
        subject=f"Ya tienes una cuenta en {APP_NAME}",
        title="Ya tienes una cuenta",
        greeting="Hola:",
        paragraphs=[
            (
                f"Alguien intentó crear una cuenta en {APP_NAME} con este correo, pero "
                "ya tiene una. No hemos cambiado nada."
            ),
            (
                "Si fuiste tú, inicia sesión con tu correo y contraseña. Si no la "
                f"recuerdas, puedes restablecerla aquí: {forgot_link}"
            ),
        ],
        action=_Action("Iniciar sesión", login_link),
        notice="Si no fuiste tú, ignora este correo: tu cuenta sigue igual.",
        tag="signup-existing-account",
    )


def signup_pending_confirmation(*, to: str, resend_link: str) -> OutgoingEmail:
    """Pidió recuperar la contraseña de un registro que aún no confirma el correo."""
    return _email(
        to=to,
        subject=f"Tu registro en {APP_NAME} está pendiente de confirmar",
        title="Confirma tu correo primero",
        greeting="Hola:",
        paragraphs=[
            (
                "Pediste restablecer tu contraseña, pero tu registro todavía está "
                "pendiente de confirmar el correo."
            ),
            (
                "Abre el enlace de confirmación que te enviamos al registrarte. Si no lo "
                "encuentras, pide otro con el botón de abajo."
            ),
        ],
        action=_Action("Enviar otro enlace", resend_link),
        notice=f"Si no te registraste en {APP_NAME}, ignora este correo.",
        tag="signup-pending",
    )


def password_reset(
    *, to: str, username: str, link: str, ttl: timedelta
) -> OutgoingEmail:
    return _email(
        to=to,
        subject=f"Restablece tu contraseña de {APP_NAME}",
        title="Restablece tu contraseña",
        greeting=f"Hola, {username}:",
        paragraphs=[
            (
                "Pulsa el botón para elegir una contraseña nueva. Al hacerlo se cerrará "
                "tu sesión en todos tus dispositivos."
            )
        ],
        action=_Action("Elegir contraseña nueva", link),
        notice=f"El enlace caduca en {describe_ttl(ttl)} y solo funciona una vez. Si no lo "
        "pediste tú, ignora este correo: tu contraseña sigue igual.",
        tag="reset-password",
    )


def password_changed(*, to: str, username: str, forgot_link: str) -> OutgoingEmail:
    """Aviso después de restablecer o cambiar la contraseña."""
    return _email(
        to=to,
        subject=f"Tu contraseña de {APP_NAME} cambió",
        title="Tu contraseña cambió",
        greeting=f"Hola, {username}:",
        paragraphs=[
            (
                "La contraseña de tu cuenta acaba de cambiar y cerramos la sesión en tus "
                "otros dispositivos."
            ),
        ],
        notice="Si no fuiste tú, restablece tu contraseña cuanto antes desde "
        f"{forgot_link}.",
        tag="password-changed",
    )
