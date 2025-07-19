"""Esquemas de respuesta para errores estandarizados."""

from typing import Optional, Any, List
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Detalle específico de un error."""

    loc: Optional[List[str]] = None  # Ubicación del error (para validaciones)
    msg: str  # Mensaje descriptivo del error
    type: str  # Tipo de error
    input: Optional[Any] = None  # Valor que causó el error (opcional)


class StandardErrorResponse(BaseModel):
    """Respuesta de error estandarizada para toda la API."""

    error: bool = True
    error_code: str  # Código único del error
    message: str  # Mensaje principal del error
    details: Optional[List[ErrorDetail]] = None  # Detalles específicos (validaciones)

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "error": True,
                    "error_code": "VALIDATION_ERROR",
                    "message": "Errores de validación en los datos enviados",
                    "details": [
                        {
                            "loc": ["body", "email"],
                            "msg": "Formato de email inválido",
                            "type": "value_error.email",
                            "input": "invalid-email",
                        },
                        {
                            "loc": ["body", "password"],
                            "msg": "La contraseña debe tener al menos 8 caracteres",
                            "type": "string_too_short",
                            "input": "short-password",
                        },
                    ],
                },
                {
                    "error": True,
                    "error_code": "NOT_FOUND_USER",
                    "message": "Usuario no encontrado",
                    "details": None,
                },
            ]
        }
