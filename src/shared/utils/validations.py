"""Utilidades para validación."""

import re
from typing import List
from pydantic import EmailStr
from email_validator import validate_email, EmailNotValidError


def validate_email_format(email: EmailStr) -> bool:
    """Valida formato de email."""
    try:
        validate_email(str(email))
        return True
    except EmailNotValidError:
        return False


def validate_password_strength(password: str) -> List[str]:
    """Valida la fortaleza de una contraseña."""
    errors = []

    if len(password) < 8:
        errors.append("La contraseña debe tener al menos 8 caracteres")

    if not re.search(r"[A-Z]", password):
        errors.append("La contraseña debe tener al menos una letra mayúscula")

    if not re.search(r"[a-z]", password):
        errors.append("La contraseña debe tener al menos una letra minúscula")

    if not re.search(r"\d", password):
        errors.append("La contraseña debe tener al menos un número")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("La contraseña debe tener al menos un carácter especial")

    return errors


def validate_currency_code(currency: str) -> bool:
    """Valida código de moneda ISO."""
    valid_currencies = ["MXN", "USD", "EUR", "GBP", "CAD", "JPY", "CHF", "AUD"]
    return currency.upper() in valid_currencies


def validate_phone_number(phone: str) -> bool:
    """Valida formato de número telefónico."""
    # Formato mexicano básico
    pattern = r"^(\+52|52)?[\s\-]?(\d{2})[\s\-]?(\d{4})[\s\-]?(\d{4})$"
    return bool(re.match(pattern, phone))


def sanitize_string(input_str: str, max_length: int = None) -> str:
    """Sanitiza una cadena de texto."""
    if not input_str:
        return ""

    # Remover espacios extra
    sanitized = " ".join(input_str.split())

    # Truncar si es necesario
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip()

    return sanitized


def validate_required_fields(data: dict, required_fields: List[str]) -> List[str]:
    """Valída campos requeridos en un diccionario."""
    errors = []

    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            errors.append(f"El campo '{field}' es requerido")

    return errors
