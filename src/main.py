from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Importar la nueva estructura
from presentation.api.v2.router import api_router  # Nueva estructura
from presentation.middleware.exception_handler import (
    lunance_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)
from shared.exceptions.base import LunanceException

# from OLD.api import api_router as old_api_router  # Backup temporal

app = FastAPI(
    title="Lunance IA - Your Personal Intelligence Assistant",
    description="Manage your finances efficiently with our API",
    version="2.0.0",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar manejadores de excepciones
app.add_exception_handler(LunanceException, lunance_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Incluir rutas de la nueva arquitectura
app.include_router(api_router, prefix="/api/v2")


# Temporalmente, mantener las rutas viejas como backup
# app.include_router(old_api_router, prefix="/api/v1/old")


@app.get("/")
async def root():
    return {
        "message": "Lunance API - Clean Architecture",
        "version": "2.0.0",
        "architecture": "Clean Architecture + DDD",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "architecture": "clean"}
