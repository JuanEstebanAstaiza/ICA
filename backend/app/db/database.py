"""
Configuración de base de datos PostgreSQL.
Diseñada para alta concurrencia e integridad transaccional.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..core.config import settings

# Configuración del motor PostgreSQL con pool de conexiones
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG
)

# Sesión de base de datos
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para modelos declarativos
Base = declarative_base()


def get_db():
    """
    Dependency para obtener sesión de base de datos.
    Garantiza cierre correcto de conexión.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializa las tablas de la base de datos.
    Importa todos los modelos para asegurar que se registren en Base.metadata
    antes de crear las tablas con todas sus columnas.
    """
    # Importar todos los modelos para que se registren en Base.metadata
    # Esto asegura que todas las columnas se creen automáticamente
    from ..models import models  # noqa: F401
    
    # Crear todas las tablas definidas en los modelos
    Base.metadata.create_all(bind=engine)
