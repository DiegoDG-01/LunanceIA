from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importar la nueva estructura
from presentation.api.v2.router import api_router  # Nueva estructura

# from OLD.api import api_router as old_api_router  # Backup temporal

app = FastAPI(
    title="Lunance IA - Your Personal Intelligence Assistant",
    description="Manage your finances efficiently with our API",
    version="2.0.0",  # Nueva versión con Clean Architecture
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas de la nueva arquitectura
app.include_router(api_router, prefix="/api/v2")


# Temporalmente, mantener las rutas viejas como backup
# app.include_router(old_api_router, prefix="/api/v1/old")

@app.get("/")
async def root():
    return {
        "message": "Lunance API - Clean Architecture",
        "version": "2.0.0",
        "architecture": "Clean Architecture + DDD"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "architecture": "clean"}
