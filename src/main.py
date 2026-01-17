import logging
from infrastructure.config.logging_config import setup_logging

setup_logging()

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from infrastructure.config.settings import settings
from infrastructure.database.connection import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Importar la nueva estructura
from presentation.api.v2.router import api_router  # Nueva estructura
from presentation.middleware.exception_handler import (
    lunance_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler,
    rate_limit_exceeded_handler,
)
from shared.exceptions.base import LunanceException
from presentation.middleware.request_logging import RequestLoggingMiddleware

# Configurar rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    for handler in logging.getLogger().handlers:
        if hasattr(handler, "close"):
            handler.flush()
            handler.close()


app = FastAPI(
    title="Lunance IA - Your Personal Intelligence Assistant",
    description="Manage your finances efficiently with our API",
    version="2.0.0",
)

# Agregar el limiter al estado de la app
app.state.limiter = limiter

# Configurar CORS
if settings.ENVIRONMENT.upper() == "PROD":
    origins = ["https://api.lunance.app"]  # Configurar dominio de producción
elif settings.ENVIRONMENT.upper() == "DEV":
    origins = ["*"]
else:
    raise ValueError("Invalid environment")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

# Registrar manejadores de excepciones
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(LunanceException, lunance_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Incluir rutas de la nueva arquitectura
app.include_router(api_router, prefix="/api/v2")


@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request):
    return {
        "message": "Hello World",
        "version": "3.0.0",
    }


@app.get("/health")
@limiter.limit("5/minute")
async def health_check(
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    try:
        db.execute(text("SELECT 1"))
        db_status = {"status": "healthy"}
    except Exception:
        db_status = {"status": "unhealthy"}

    return {
        "API": "healthy",
        "version": "3.0.0",
        "services":db_status
    }
