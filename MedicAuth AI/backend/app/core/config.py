"""
Configuración de la aplicación
"""

from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Configuración global de la aplicación"""
    
    # API Settings
    PROJECT_NAME: str = "MedicAuth AI"
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
    GEMINI_API_KEY: str
    OPENAI_API_KEY: str = ""  # Opcional, para embeddings
    
    # ChromaDB (Vector Store)
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    WEBHOOK_SECRET_TOKEN: str = "medicauth_secret_hack_2026"

    # Cloudinary
    CLOUDINARY_URL: str = ""
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    def __init__(self, **data):
        super().__init__(**data)
        # Parse CLOUDINARY_URL if provided
        if self.CLOUDINARY_URL and "cloudinary://" in self.CLOUDINARY_URL:
            try:
                # Format: cloudinary://api_key:api_secret@cloud_name
                url = self.CLOUDINARY_URL.replace("cloudinary://", "")
                creds, cloud = url.split("@")
                api_key, api_secret = creds.split(":")
                self.CLOUDINARY_API_KEY = api_key
                self.CLOUDINARY_API_SECRET = api_secret
                self.CLOUDINARY_CLOUD_NAME = cloud
            except Exception as e:
                print(f"Error parsing CLOUDINARY_URL: {e}")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
