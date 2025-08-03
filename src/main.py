from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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

# Configurar rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Lunance IA - Your Personal Intelligence Assistant",
    description="Manage your finances efficiently with our API",
    version="2.0.0",
)

# Agregar el limiter al estado de la app
app.state.limiter = limiter

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar manejadores de excepciones
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(LunanceException, lunance_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Incluir rutas de la nueva arquitectura
app.include_router(api_router, prefix="/api/v2")


@app.get("/")
@limiter.limit("100/minute")
async def root(request: Request):
    return {
        "message": "Lunance API - Clean Architecture",
        "version": "2.0.0",
    }


@app.get("/health")
@limiter.limit("10/minute")
async def health_check(request: Request):
    return {"status": "healthy", "version": "2.0.0", "hello": "world"}
