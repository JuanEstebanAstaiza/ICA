# Guía de Despliegue On-Premise

## 📋 Introducción

Esta guía detalla el proceso de despliegue del Sistema ICA en la infraestructura de cada alcaldía. 

> ⚠️ **Importante**: Este software es un SaaS instalable (self-hosted / on-premise) que se despliega directamente en la infraestructura de cada alcaldía. La seguridad, disponibilidad, redes, backups y hardening de infraestructura son responsabilidad exclusiva del área TI de la alcaldía contratante.

## 🖥️ Requisitos del Sistema

### Hardware Mínimo

| Componente | Requisito Mínimo | Recomendado |
|------------|------------------|-------------|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Disco | 100 GB SSD | 500 GB SSD |
| Red | 100 Mbps | 1 Gbps |

### Software

- **Sistema Operativo**: Ubuntu 22.04 LTS / RHEL 8+ / Rocky Linux 8+
- **Python**: 3.10 o superior
- **PostgreSQL**: 14 o superior
- **Redis**: 7.0+ (opcional, para cache y rate limiting)
- **Nginx**: Como proxy inverso (recomendado)
- **Supervisor/systemd**: Para gestión de procesos

## 📦 Preparación del Servidor

### 1. Actualizar Sistema

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# RHEL/Rocky Linux
sudo dnf update -y
```

### 2. Instalar Dependencias

```bash
# Ubuntu/Debian
sudo apt install -y python3.10 python3.10-venv python3-pip \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    supervisor \
    git

# RHEL/Rocky Linux
sudo dnf install -y python3.10 python3-pip \
    postgresql-server postgresql-contrib \
    redis \
    nginx \
    supervisor \
    git
```

### 3. Configurar PostgreSQL

```bash
# Iniciar PostgreSQL
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Crear usuario y base de datos
sudo -u postgres psql << EOF
CREATE USER ica_user WITH PASSWORD 'secure_password_here';
CREATE DATABASE ica_db OWNER ica_user;
GRANT ALL PRIVILEGES ON DATABASE ica_db TO ica_user;
\q
EOF
```

### 4. Configurar Redis (Opcional)

```bash
sudo systemctl enable redis
sudo systemctl start redis
```

## 🚀 Instalación de la Aplicación

### 1. Crear Usuario de Aplicación

```bash
sudo useradd -m -s /bin/bash ica
sudo mkdir -p /opt/ica
sudo chown ica:ica /opt/ica
```

### 2. Clonar Repositorio

```bash
sudo -u ica git clone <REPO_URL> /opt/ica/app
```

### 3. Configurar Entorno Virtual

```bash
cd /opt/ica/app/backend
sudo -u ica python3.10 -m venv venv
sudo -u ica ./venv/bin/pip install --upgrade pip
sudo -u ica ./venv/bin/pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

```bash
sudo -u ica cp .env.example .env
sudo nano /opt/ica/app/backend/.env
```

Contenido del archivo `.env`:

```env
# Aplicación
APP_NAME="Alcaldía de [MUNICIPIO] - Sistema ICA"
APP_VERSION="1.0.0"
DEBUG=false

# Servidor
HOST=127.0.0.1
PORT=8000

# Base de datos
DATABASE_URL=postgresql://ica_user:secure_password_here@localhost:5432/ica_db

# Redis (opcional)
REDIS_URL=redis://localhost:6379/0

# Seguridad - CAMBIAR EN PRODUCCIÓN
SECRET_KEY=generar-clave-segura-de-al-menos-64-caracteres-aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Argon2
ARGON2_TIME_COST=2
ARGON2_MEMORY_COST=65536
ARGON2_PARALLELISM=1

# Almacenamiento
PDF_STORAGE_PATH=/var/ica/pdfs
ASSETS_STORAGE_PATH=/var/ica/assets

# CORS - Ajustar según dominio
CORS_ORIGINS=https://ica.alcaldia.gov.co

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
```

### 5. Crear Directorios de Almacenamiento

```bash
sudo mkdir -p /var/ica/{pdfs,assets}
sudo chown -R ica:ica /var/ica
sudo chmod 750 /var/ica
```

### 6. Inicializar Base de Datos

```bash
cd /opt/ica/app/backend
sudo -u ica ./venv/bin/python -c "from app.db.database import init_db; init_db()"
```

## ⚙️ Configuración de Servicios

### 1. Configurar Supervisor

```bash
sudo nano /etc/supervisor/conf.d/ica.conf
```

```ini
[program:ica]
command=/opt/ica/app/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
directory=/opt/ica/app/backend
user=ica
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/ica/app.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
environment=
    PATH="/opt/ica/app/backend/venv/bin:%(ENV_PATH)s",
    PYTHONPATH="/opt/ica/app/backend"
```

```bash
sudo mkdir -p /var/log/ica
sudo chown ica:ica /var/log/ica
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start ica
```

### 2. Configurar Nginx

```bash
sudo nano /etc/nginx/sites-available/ica
```

```nginx
server {
    listen 80;
    server_name ica.alcaldia.gov.co;
    
    # Redirigir a HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ica.alcaldia.gov.co;
    
    # Certificados SSL (configurar según infraestructura)
    ssl_certificate /etc/ssl/certs/ica.crt;
    ssl_certificate_key /etc/ssl/private/ica.key;
    
    # Configuración SSL
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    
    # Headers de seguridad
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Frontend estático
    location /static {
        alias /opt/ica/app/frontend;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }
    
    # API Backend
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Página principal
    location / {
        root /opt/ica/app/frontend/templates;
        index login.html;
        try_files $uri $uri/ /login.html;
    }
    
    # Logs
    access_log /var/log/nginx/ica_access.log;
    error_log /var/log/nginx/ica_error.log;
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ica /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔒 Configuración de Seguridad

### 1. Firewall

```bash
# UFW (Ubuntu)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# firewalld (RHEL/Rocky)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. SELinux (RHEL/Rocky)

```bash
sudo setsebool -P httpd_can_network_connect 1
```

### 3. Permisos de Archivos

```bash
# Aplicación
sudo chown -R ica:ica /opt/ica
sudo chmod -R 750 /opt/ica

# Almacenamiento
sudo chown -R ica:ica /var/ica
sudo chmod -R 750 /var/ica
```

## 📊 Monitoreo y Logs

### Ubicación de Logs

| Log | Ubicación |
|-----|-----------|
| Aplicación | `/var/log/ica/app.log` |
| Nginx Acceso | `/var/log/nginx/ica_access.log` |
| Nginx Errores | `/var/log/nginx/ica_error.log` |
| PostgreSQL | `/var/log/postgresql/` |

### Comandos Útiles

```bash
# Ver logs en tiempo real
sudo tail -f /var/log/ica/app.log

# Estado de servicios
sudo supervisorctl status ica
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis

# Reiniciar aplicación
sudo supervisorctl restart ica
```

## 💾 Respaldos

### Script de Respaldo

```bash
#!/bin/bash
# /opt/ica/scripts/backup.sh

BACKUP_DIR="/var/backups/ica"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Respaldo de base de datos
pg_dump -U ica_user ica_db > "$BACKUP_DIR/db_$DATE.sql"

# Respaldo de PDFs
tar -czf "$BACKUP_DIR/pdfs_$DATE.tar.gz" /var/ica/pdfs

# Respaldo de assets
tar -czf "$BACKUP_DIR/assets_$DATE.tar.gz" /var/ica/assets

# Eliminar respaldos mayores a 30 días
find $BACKUP_DIR -type f -mtime +30 -delete
```

```bash
sudo chmod +x /opt/ica/scripts/backup.sh

# Agregar a crontab (diario a las 2 AM)
echo "0 2 * * * /opt/ica/scripts/backup.sh" | sudo crontab -
```

## ✅ Verificación Post-Instalación

1. **Verificar servicios:**
   ```bash
   sudo supervisorctl status ica
   sudo systemctl status nginx postgresql redis
   ```

2. **Verificar endpoints:**
   ```bash
   curl -k https://localhost/api/v1/health
   curl -k https://localhost/api/docs
   ```

3. **Verificar logs:**
   ```bash
   sudo tail -20 /var/log/ica/app.log
   ```

4. **Crear usuario administrador inicial:**
   ```bash
   cd /opt/ica/app/backend
   ./venv/bin/python -c "
   from app.db.database import SessionLocal
   from app.models.models import User, UserRole
   from app.core.security import get_password_hash
   
   db = SessionLocal()
   admin = User(
       email='admin@alcaldia.gov.co',
       hashed_password=get_password_hash('SecurePassword123!'),
       full_name='Administrador del Sistema',
       role=UserRole.ADMIN_SISTEMA
   )
   db.add(admin)
   db.commit()
   print('Usuario administrador creado exitosamente')
   "
   ```

## ⚠️ Consideraciones Importantes

1. **SSL/TLS**: Es obligatorio usar HTTPS en producción
2. **Actualizaciones**: Mantener el sistema y dependencias actualizados
3. **Respaldos**: Configurar respaldos automáticos diarios
4. **Monitoreo**: Implementar alertas para caídas de servicio
5. **Auditoría**: Revisar logs de auditoría regularmente

## 📞 Soporte

Para soporte técnico, contactar al proveedor del software.

---

**Nota**: El proveedor no garantiza disponibilidad si la infraestructura falla. El uso depende de la correcta operación del área TI institucional.
