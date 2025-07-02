from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Schema de respuesta para tokens."""
    access_token: str = Field(..., description="Access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field(default="bearer", description="Tipo de token")


class RegisterResponse(BaseModel):
    """Schema de respuesta para registro."""
    user_id: int = Field(..., description="ID del usuario")
    name: str = Field(..., description="Nombre del usuario")
    email: str = Field(..., description="Email del usuario")
    message: str = Field(..., description="Mensaje de confirmación")


class UserInfoResponse(BaseModel):
    """Schema de respuesta para información del usuario."""
    user_id: int = Field(..., description="ID del usuario")
    name: str = Field(..., description="Nombre del usuario")
    email: str = Field(..., description="Email del usuario")
    is_active: bool = Field(..., description="Estado del usuario")
