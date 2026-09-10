"""Utilidades para manejo de idiomas."""

from fastapi import Request


def detect_language_from_request(request: Request) -> str:
    """
    Detects the user's preferred language from a FastAPI request.

    Checks for a supported language code ("es" or "en") in the query parameter `lang`, then in the `Accept-Language` header, and defaults to "es" if neither is found.

    Returns:
        str: The detected language code ("es" or "en").
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


def get_user_language(request: Request | None = None) -> str:
    """
    Return the user's language code, defaulting to Spanish ("es") if no request is provided.

    If a FastAPI request is given, the language is determined from the request's query parameters or headers. Otherwise, Spanish ("es") is returned.

    Returns:
        str: The language code, either "es" or "en".
    """
    if request:
        return detect_language_from_request(request)
    return "es"  # Default
