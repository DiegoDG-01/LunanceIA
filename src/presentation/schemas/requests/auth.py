from pydantic import BaseModel, Field, EmailStr


class LoginRequest(BaseModel):
    """Schema para login."""
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=1, description="Contraseña")


class RegisterRequest(BaseModel):
    """Schema para registro."""
    name: str = Field(..., min_length=1, max_length=100, description="Nombre del usuario")
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=8, description="Contraseña")


class RefreshTokenRequest(BaseModel):
    """Schema para refresh token."""
    refresh_token: str = Field(..., description="Refresh token")
