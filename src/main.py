from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.api import api_router
from config import settings

app = FastAPI(
    title="Lunance IA - Your Personal Finance Assistant",
    description="Manage your finances efficiently with our API",
    version="1.0.0",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "API de Finanzas Personales"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}