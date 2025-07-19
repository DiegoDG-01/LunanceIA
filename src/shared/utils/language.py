"""Utilidades para manejo de idiomas."""

from typing import Optional
from fastapi import Request


def detect_language_from_request(request: Request) -> str:
    """
    Detecta el idioma preferido del usuario desde el request.

    Prioridad:
    1. Query parameter ?lang=es/en
    2. Header Accept-Language
    3. Default: español

    Args:
        request: Request de FastAPI

    Returns:
        Código de idioma ("es" o "en")
    """
    # 1. Verificar query parameter
    lang_param = request.query_params.get("lang")
    if lang_param in ["es", "en"]:
        return lang_param

    # 2. Verificar header Accept-Language
    accept_language = request.headers.get("Accept-Language", "")

    # Parsear Accept-Language header
    if accept_language:
        # Ejemplo: "en-US,en;q=0.9,es;q=0.8"
        languages = []
        for lang_spec in accept_language.split(","):
            lang_code = lang_spec.split(";")[0].strip().lower()
            # Tomar solo los primeros 2 caracteres (en-US -> en)
            lang_code = lang_code[:2]
            if lang_code in ["es", "en"]:
                languages.append(lang_code)

        # Retornar el primer idioma soportado
        if languages:
            return languages[0]

    # 3. Default a español
    return "es"


def get_user_language(request: Optional[Request] = None) -> str:
    """
    Obtiene el idioma del usuario, con fallback a español.

    Args:
        request: Request de FastAPI (opcional)

    Returns:
        Código de idioma ("es" o "en")
    """
    if request:
        return detect_language_from_request(request)
    return "es"  # Default
