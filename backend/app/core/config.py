"""
Configuración central de la aplicación ICA.
Basado en el documento: Documents/formulario-ICA.md
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """
    Configuración de la aplicación.
    Los valores se cargan desde variables de entorno para seguridad.
    """
    # Application
    APP_NAME: str = "Formulario Único Nacional ICA"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database - PostgreSQL
    DATABASE_URL: str = "postgresql://ica_user:ica_password@localhost:5432/ica_db"
    
    # Redis (optional)
    REDIS_URL: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password hashing (Argon2)
    ARGON2_TIME_COST: int = 2
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 1
    
    # PDF Storage - Local filesystem
    PDF_STORAGE_PATH: str = "/var/ica/pdfs"
    
    # White-label assets
    ASSETS_STORAGE_PATH: str = "/var/ica/assets"
    
    # CORS
    CORS_ORIGINS: str = "*"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def get_pdf_path(year: int, municipality: str, user_id: int) -> str:
    """
    Genera la ruta de almacenamiento del PDF organizada por año, municipio y usuario.
    Basado en requerimiento: "Organizarse por año, municipio y usuario"
    """
    base_path = settings.PDF_STORAGE_PATH
    return os.path.join(base_path, str(year), municipality, str(user_id))
