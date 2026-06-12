"""
MedicAuth AI - Backend
Agente Inteligente de Pre-Autorización Quirúrgica en Tiempo Real
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import cloudinary

from app.core.config import settings
from app.api.routes import webhook, authorization, health

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de inicio y cierre de la aplicación"""
    # Startup
    print("Iniciando MedicAuth AI...")
    print(f"Notion DB Solicitudes: {settings.NOTION_SOLICITUDES_DB_ID[:8]}...")
    print(f"Notion DB Pólizas: {settings.NOTION_POLIZAS_DB_ID[:8]}...")

    # Inicializar Cloudinary con credenciales
    if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
        print(" Cloudinary configurado")
    else:
        print(" Cloudinary no configurado - falta CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY o CLOUDINARY_API_SECRET")

    yield
    # Shutdown
    print("Cerrando SurgeryAuth AI...")

app = FastAPI(
    title="MedicAuth AI API",
    description="API para autorización quirúrgica inteligente",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - Permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(webhook.router, prefix="/api/webhook", tags=["Webhook"])
app.include_router(authorization.router, prefix="/api/authorization", tags=["Authorization"])

@app.get("/")
async def root():
    return {
        "message": "MedicAuth AI - API activa",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
