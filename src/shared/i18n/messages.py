def get_error_message(code: str, lang: str = "es") -> str:
    return ERROR_MESSAGES[lang][code]


ERROR_MESSAGES = {
    "es": {
        "EMAIL_REQUIRED": "El email es requerido",
        "EMAIL_INVALID_FORMAT": "Formato de email inválido",

        "PASSWORD_TOO_SHORT": "La contraseña debe tener al menos 8 caracteres",
        "PASSWORD_MISSING_UPPERCASE": "La contraseña debe incluir al menos una mayúscula",
        "PASSWORD_MISSING_LOWERCASE": "La contraseña debe incluir al menos una minúscula",
        "PASSWORD_MISSING_DIGIT": "La contraseña debe incluir al menos un número",
        "PASSWORD_MISSING_SPECIAL": "La contraseña debe incluir al menos un carácter especial",

        "REFRESH_TOKEN_INVALID": "El token de refresco es inválido",
    },
    "en": {
        "EMAIL_REQUIRED": "Email is required",
        "EMAIL_INVALID_FORMAT": "Invalid email format",

        "PASSWORD_TOO_SHORT": "Password must be at least 8 characters",
        "PASSWORD_MISSING_UPPERCASE": "Password must include at least one uppercase letter",
        "PASSWORD_MISSING_LOWERCASE": "Password must include at least one lowercase letter",
        "PASSWORD_MISSING_DIGIT": "Password must include at least one number",
        "PASSWORD_MISSING_SPECIAL": "Password must include at least one special character",

        "REFRESH_TOKEN_INVALID": "Refresh token is invalid",
    },
}
