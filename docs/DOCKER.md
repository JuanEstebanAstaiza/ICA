# 🐋 Guía de Docker para Sistema ICA

Esta guía proporciona instrucciones detalladas para ejecutar el Sistema ICA utilizando Docker y Docker Compose.

## 📋 Índice

- [Requisitos Previos](#requisitos-previos)
- [Instalación de Docker](#instalación-de-docker)
- [Ejecución Rápida](#ejecución-rápida)
- [Comandos Útiles](#comandos-útiles)
- [Configuración Avanzada](#configuración-avanzada)
- [Troubleshooting](#troubleshooting)
- [Producción](#producción)

## 📦 Requisitos Previos

### Software Necesario

- **Docker Engine**: 20.10 o superior
- **Docker Compose**: 2.0 o superior
- **Git**: Para clonar el repositorio
- **Mínimo 4GB RAM** disponible para los contenedores
- **10GB de espacio en disco**

### Verificar Instalación

```bash
docker --version
docker compose version
```

## 🔧 Instalación de Docker

### Ubuntu/Debian

```bash
# Actualizar repositorios
sudo apt update

# Instalar dependencias
sudo apt install -y ca-certificates curl gnupg lsb-release

# Agregar llave GPG de Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Agregar repositorio
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Agregar usuario al grupo docker (opcional, para no usar sudo)
sudo usermod -aG docker $USER
newgrp docker
```

### Windows

1. Descargar [Docker Desktop para Windows](https://www.docker.com/products/docker-desktop)
2. Ejecutar el instalador
3. Reiniciar el sistema
4. Abrir Docker Desktop y esperar a que inicie

### macOS

1. Descargar [Docker Desktop para Mac](https://www.docker.com/products/docker-desktop)
2. Arrastrar Docker.app a la carpeta Aplicaciones
3. Abrir Docker Desktop
4. Esperar a que el ícono de Docker aparezca en la barra de menú

## 🚀 Ejecución Rápida

### 1. Clonar el Repositorio

```bash
git clone https://github.com/JuanEstebanAstaiza/ICA.git
cd ICA
```

### 2. Iniciar Todos los Servicios

```bash
docker compose up -d
```

Este comando:
- ✅ Descarga las imágenes necesarias (PostgreSQL, Redis, Nginx)
- ✅ Construye la imagen del backend
- ✅ Construye la imagen del frontend
- ✅ Crea los contenedores
- ✅ Inicia todos los servicios
- ✅ Configura la red interna
- ✅ Crea volúmenes persistentes

### 3. Verificar que los Servicios Están Corriendo

```bash
docker compose ps
```

Deberías ver algo como:

```
NAME                IMAGE               STATUS              PORTS
ica_frontend        ica-frontend        Up (healthy)        0.0.0.0:3000->80/tcp
ica_backend         ica-backend         Up (healthy)        0.0.0.0:8000->8000/tcp
ica_postgres        postgres:15-alpine  Up (healthy)        0.0.0.0:5432->5432/tcp
ica_redis           redis:7-alpine      Up (healthy)        0.0.0.0:6379->6379/tcp
```

### 4. Acceder a la Aplicación

Una vez que los servicios estén corriendo:

- **Frontend (Interfaz de Usuario)**: http://localhost:3000
- **API Backend**: http://localhost:8000
- **Documentación Swagger**: http://localhost:8000/api/docs
- **Documentación ReDoc**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health

### 5. Ver Logs en Tiempo Real

```bash
# Todos los servicios
docker compose logs -f

# Solo el backend
docker compose logs -f backend

# Solo PostgreSQL
docker compose logs -f postgres
```

### 6. Detener los Servicios

```bash
# Detener sin eliminar contenedores
docker compose stop

# Detener y eliminar contenedores (los datos persisten)
docker compose down

# Detener, eliminar contenedores Y volúmenes (⚠️ elimina todos los datos)
docker compose down -v
```

## 🛠️ Comandos Útiles

### Gestión de Servicios

```bash
# Iniciar servicios
docker compose up -d

# Reiniciar un servicio específico
docker compose restart backend

# Reconstruir imágenes
docker compose build

# Reconstruir sin caché
docker compose build --no-cache

# Ver estado de servicios
docker compose ps

# Ver recursos utilizados
docker compose stats
```

### Acceso a Contenedores

```bash
# Ejecutar comando en el backend
docker compose exec backend bash

# Ejecutar comando en PostgreSQL
docker compose exec postgres psql -U ica_user -d ica_db

# Ver logs de un servicio
docker compose logs backend

# Seguir logs en tiempo real
docker compose logs -f backend
```

### Base de Datos

```bash
# Conectar a PostgreSQL
docker compose exec postgres psql -U ica_user -d ica_db

# Backup de base de datos
docker compose exec postgres pg_dump -U ica_user ica_db > backup.sql

# Restaurar base de datos
docker compose exec -T postgres psql -U ica_user -d ica_db < backup.sql

# Ver tablas
docker compose exec postgres psql -U ica_user -d ica_db -c "\dt"
```

### Limpieza

```bash
# Eliminar contenedores detenidos
docker compose down

# Eliminar contenedores y volúmenes
docker compose down -v

# Limpiar imágenes no utilizadas
docker image prune -a

# Limpiar todo (contenedores, imágenes, volúmenes)
docker system prune -a --volumes
```

## ⚙️ Configuración Avanzada

### Variables de Entorno Personalizadas

Puedes sobrescribir variables creando un archivo `.env`:

```bash
cp .env.example .env
nano .env
```

Ejemplo de `.env`:

```env
# Aplicación
APP_NAME="Mi Alcaldía - Sistema ICA"
DEBUG=false

# Base de datos
DATABASE_URL=postgresql://ica_user:mi_password_seguro@postgres:5432/ica_db

# Seguridad
SECRET_KEY=mi-clave-super-secreta-de-64-caracteres-minimo-generada-aleatoriamente

# CORS (dominios permitidos)
CORS_ORIGINS=https://mi-dominio.gov.co,https://www.mi-dominio.gov.co
```

### Cambiar Puertos

Edita el `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "9000:8000"  # Cambia el puerto externo
```

### Volúmenes en Ubicación Específica

```yaml
volumes:
  pdf_storage:
    driver: local
    driver_opts:
      type: none
      device: /ruta/personalizada/pdfs
      o: bind
```

### Aumentar Recursos

En `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## 🔍 Troubleshooting

### Problema: Los servicios no inician

**Solución:**
```bash
# Ver logs detallados
docker compose logs

# Ver estado de salud
docker compose ps

# Revisar si los puertos están ocupados
sudo netstat -tulpn | grep -E '8000|5432|6379'
```

### Problema: Error de conexión a base de datos

**Solución:**
```bash
# Verificar que PostgreSQL esté saludable
docker compose ps postgres

# Ver logs de PostgreSQL
docker compose logs postgres

# Probar conexión manual
docker compose exec postgres pg_isready -U ica_user
```

### Problema: Backend no responde

**Solución:**
```bash
# Ver logs del backend
docker compose logs backend

# Verificar health check
curl http://localhost:8000/health

# Reiniciar el servicio
docker compose restart backend
```

### Problema: Error de permisos

**Solución:**
```bash
# En Linux, agregar usuario al grupo docker
sudo usermod -aG docker $USER
newgrp docker

# O ejecutar con sudo (no recomendado para producción)
sudo docker compose up -d
```

### Problema: Puerto ya en uso

**Solución:**
```bash
# Encontrar qué está usando el puerto
sudo lsof -i :8000

# Cambiar el puerto en docker-compose.yml
# O detener el servicio que lo usa
```

### Problema: Sin espacio en disco

**Solución:**
```bash
# Limpiar imágenes no utilizadas
docker image prune -a

# Limpiar volúmenes huérfanos
docker volume prune

# Ver uso de espacio
docker system df
```

### Problema: Contenedor se reinicia constantemente

**Solución:**
```bash
# Ver por qué falla
docker compose logs backend

# Ver últimas líneas del log
docker compose logs --tail=100 backend

# Ejecutar sin el flag -d para ver errores
docker compose up backend
```

## 🚀 Producción

### Recomendaciones de Seguridad

1. **No usar variables por defecto**
   ```bash
   # Generar SECRET_KEY seguro
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```

2. **Usar contraseñas fuertes**
   ```env
   POSTGRES_PASSWORD=contraseña-muy-segura-y-aleatoria
   ```

3. **Configurar CORS específicamente**
   ```env
   CORS_ORIGINS=https://mi-dominio.gov.co
   ```

4. **Usar volúmenes específicos**
   ```bash
   # Crear directorios con permisos específicos
   sudo mkdir -p /var/ica/{pdfs,assets}
   sudo chown -R 1000:1000 /var/ica
   ```

5. **Configurar backup automático**
   ```bash
   # Script en crontab
   0 2 * * * docker compose exec postgres pg_dump -U ica_user ica_db > /backups/ica_$(date +\%Y\%m\%d).sql
   ```

### Docker con Nginx

Para producción, usar Nginx como proxy reverso:

```yaml
# docker-compose.prod.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
```

### Logs y Monitoreo

```bash
# Configurar rotación de logs
docker compose --log-opt max-size=10m --log-opt max-file=3 up -d

# Ver métricas
docker stats
```

### Actualizaciones

```bash
# Obtener última versión
git pull

# Reconstruir imagen
docker compose build

# Reiniciar con nueva versión (sin downtime)
docker compose up -d --no-deps --build backend
```

## 📊 Verificación de Instalación

Después de iniciar los servicios, verifica:

```bash
# 1. Estado de servicios
docker compose ps

# 2. Health checks
curl http://localhost:8000/health

# 3. Base de datos
docker compose exec postgres psql -U ica_user -d ica_db -c "SELECT version();"

# 4. Redis
docker compose exec redis redis-cli ping

# 5. Ver API documentation
# Abrir en navegador: http://localhost:8000/api/docs
```

## 🆘 Soporte

Si encuentras problemas:

1. Revisa los logs: `docker compose logs`
2. Verifica el estado: `docker compose ps`
3. Consulta esta guía
4. Reporta el issue en GitHub con los logs relevantes

## 📚 Recursos Adicionales

- [Documentación oficial de Docker](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Best practices para Dockerfile](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Documentación del Sistema ICA](./DOCUMENTACION_COMPLETA.md)

---

**¡El sistema está listo para usar con Docker! 🎉**
