import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

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
    rate_limit_exceeded_handler,
)
from presentation.middleware.request_logging import RequestLoggingMiddleware
from shared.exceptions.base import LunanceException

# Configurar logging
setup_logging()

# Configurar rate limiter
limiter = Limiter(
    key_func=get_remote_address, enabled=settings.ENVIRONMENT.upper() != "TEST"
)


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
    version="4.1.0",
    docs_url=False,
    redoc_url=False,
    lifespan=lifespan,
)

# Agregar el limiter al estado de la app
app.state.limiter = limiter

# Configurar CORS
if settings.ENVIRONMENT.upper() == "PROD":
    origins = [
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
        "version": "4.3.2",
    }


@app.get("/health")
@limiter.limit("5/minute")
async def health_check(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = {"status": "healthy"}
    except Exception:
        db_status = {"status": "unhealthy"}

    return {"API": "healthy", "version": "4.3.2", "services": db_status}
