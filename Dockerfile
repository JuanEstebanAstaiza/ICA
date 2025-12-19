# Dockerfile para el Sistema ICA
# Basado en Python 3.11 para mejor performance y seguridad

FROM python:3.11-slim

# Metadata
LABEL maintainer="Sistema ICA"
LABEL description="Sistema de Formulario Único Nacional de Declaración y Pago del Impuesto de Industria y Comercio"

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para seguridad
RUN groupadd -r ica && useradd -r -g ica ica

# Crear directorios de trabajo
WORKDIR /app

# Copiar requirements primero (para cachear layer)
COPY backend/requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY backend/app ./app
COPY frontend ./frontend

# Crear directorios necesarios con permisos
RUN mkdir -p /var/ica/pdfs /var/ica/assets && \
    chown -R ica:ica /var/ica /app

# Cambiar a usuario no-root
USER ica

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
