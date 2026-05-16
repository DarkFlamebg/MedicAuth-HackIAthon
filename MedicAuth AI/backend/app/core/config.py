"""
Configuración de la aplicación
"""

from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Configuración global de la aplicación"""
    
    # API Settings
    PROJECT_NAME: str = "SurgeryAuth AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",
        "https://*.vercel.app",
        "https://*.netlify.app",
    ]
    
    # Notion API
    NOTION_TOKEN: str
    NOTION_SOLICITUDES_DB_ID: str
    NOTION_POLIZAS_DB_ID: str
    NOTION_VERSION: str = "2022-06-28"
    
    # AI Services
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: str = ""  # Opcional, para embeddings
    
    # ChromaDB (Vector Store)
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
