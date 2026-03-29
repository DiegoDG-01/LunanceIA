import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from secure import Secure
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_10_per_minute,
    limiter_5_per_minute,
)

from infrastructure.config.logging_config import setup_logging
from infrastructure.config.settings import settings
from infrastructure.database.connection import get_db
from infrastructure.scheduler.service import scheduler_service
from presentation.api.v2.router import api_router
from presentation.middleware.exception_handler import (
    lunance_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)
from presentation.middleware.request_logging import RequestLoggingMiddleware
from shared.exceptions.base import LunanceException

# Configurar logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_service.start()
    yield
    scheduler_service.shutdown()

    for handler in logging.getLogger().handlers:
        if hasattr(handler, "close"):
            handler.flush()
            handler.close()


app = FastAPI(
    title="Lunance IA - Your Personal Intelligence Assistant",
    description="Manage your finances efficiently with our API",
    version="5.0.0",
    docs_url="/docs" if settings.ENVIRONMENT.upper() != "PROD" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT.upper() != "PROD" else None,
    lifespan=lifespan,
)
secure_header = Secure.with_default_headers()

# Configurar CORS
if settings.ENVIRONMENT.upper() == "PROD":
    origins = [
        "https://preview.lunance.app",
        "https://api.lunance.app",
        "https://lunance.app",
    ]
elif settings.ENVIRONMENT.upper() in ["DEV", "TEST"]:
    origins = ["http://localhost:8080"]
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
app.add_exception_handler(LunanceException, lunance_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, generic_exception_handler)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    await secure_header.set_headers_async(response)
    return response


# Incluir rutas de la nueva arquitectura
app.include_router(api_router, prefix="/api/v2")


@app.get("/")
async def root(request: Request):
    enforce_rate_limit(limiter_10_per_minute, request)
    return {
        "message": "Hello World",
        "version": "5.0.0",
    }


@app.get("/health")
async def health_check(request: Request, db: AsyncSession = Depends(get_db)):
    enforce_rate_limit(limiter_5_per_minute, request)
    try:
        await db.execute(text("SELECT 1"))
        db_status = {"status": "healthy"}
    except Exception:
        db_status = {"status": "unhealthy"}

    return {"API": "healthy", "version": "5.0.0", "services": db_status}
