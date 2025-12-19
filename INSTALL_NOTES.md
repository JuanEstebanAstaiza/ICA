# 🚨 Notas de Instalación

## Certificados SSL en Entornos Corporativos

Si encuentras errores relacionados con certificados SSL durante la construcción de Docker, como:

```
SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED]
```

Esto puede ocurrir en entornos corporativos con proxies o certificados autofirmados.

### Solución 1: Configurar Docker para usar certificados corporativos

```dockerfile
# En el Dockerfile, agregar antes de pip install:
RUN pip config set global.trusted-host "pypi.org pypi.python.org files.pythonhosted.org" \
    && pip config set global.cert "/etc/ssl/certs/ca-certificates.crt"
```

### Solución 2: Usar una imagen pre-construida

En lugar de construir localmente, puedes usar una imagen pre-construida:

```yaml
# En docker-compose.yml, cambiar:
services:
  backend:
    image: usuario/ica-backend:latest  # Usar imagen pre-construida
    # build:
    #   context: .
    #   dockerfile: Dockerfile
```

### Solución 3: Construir con pip sin verificación SSL (Solo para desarrollo)

⚠️ **SOLO para entornos de desarrollo, NUNCA en producción**

```dockerfile
# Modificar temporalmente el Dockerfile:
RUN pip install --no-cache-dir --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt
```

## Verificación del Sistema

Una vez instalado, verifica que todo funciona:

```bash
# 1. Verificar servicios
docker compose ps

# 2. Verificar logs
docker compose logs backend

# 3. Probar health check
curl http://localhost:8000/health

# 4. Acceder a documentación
# Abrir en navegador: http://localhost:8000/api/docs
```

## Soporte

Si los problemas persisten:

1. Revisa los logs: `docker compose logs`
2. Verifica la conectividad de red
3. Contacta al equipo de TI sobre configuración de proxies/certificados
4. Consulta la documentación completa en `docs/DOCKER.md`
