"""
Aplicación principal FastAPI para el Sistema ICA.
Formulario Único Nacional de Declaración y Pago del Impuesto de Industria y Comercio.

Basado en: Documents/formulario-ICA.md
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .core.config import settings
from .db.database import init_db
from .api.endpoints import auth, declarations, admin
from .api.middleware.security import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    InputSanitizationMiddleware,
    AuditLogMiddleware
)

# Crear aplicación
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## Sistema de Declaración ICA
    
    Plataforma web institucional para el diligenciamiento del 
    Formulario Único Nacional de Declaración y Pago del Impuesto 
    de Industria y Comercio (ICA).
    
    ### Funcionalidades:
    - Autenticación de usuarios
    - Creación y diligenciamiento del formulario ICA
    - Cálculo automático conforme a normativa
    - Firma digital del formulario
    - Generación de PDF institucional
    - Panel marca blanca por alcaldía
    
    ### Secciones del Formulario:
    - **Sección A**: Información del Contribuyente
    - **Sección B**: Base Gravable (Renglones 8-16)
    - **Sección C**: Actividades Gravadas
    - **Sección D**: Liquidación del Impuesto (Renglones 30-33)
    - **Sección E**: Descuentos, Créditos y Anticipos
    - **Sección F**: Total a Pagar / Saldo a Favor
    - **Sección G**: Firma y Responsabilidad
    """,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar middleware de seguridad
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(InputSanitizationMiddleware)
app.add_middleware(AuditLogMiddleware)

# Incluir routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(declarations.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

# Montar archivos estáticos para el frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.on_event("startup")
async def startup_event():
    """Inicialización al arrancar la aplicación."""
    # Crear directorios necesarios
    os.makedirs(settings.PDF_STORAGE_PATH, exist_ok=True)
    os.makedirs(settings.ASSETS_STORAGE_PATH, exist_ok=True)
    
    # Inicializar base de datos
    init_db()
    
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} iniciado")
    print(f"📄 Documentación disponible en /api/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Limpieza al cerrar la aplicación."""
    print("👋 Aplicación cerrada")


@app.get("/")
async def root():
    """Endpoint raíz."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """Health check para monitoreo."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }
