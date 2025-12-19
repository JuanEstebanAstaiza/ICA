# 🧪 Guía de Pruebas del Sistema ICA

Esta guía proporciona instrucciones para ejecutar las pruebas del sistema y verificar su correcto funcionamiento.

## 📋 Índice

- [Configuración de Entorno de Pruebas](#configuración-de-entorno-de-pruebas)
- [Ejecutar Pruebas con Docker](#ejecutar-pruebas-con-docker)
- [Pruebas Manuales](#pruebas-manuales)
- [Casos de Prueba](#casos-de-prueba)

## 🔧 Configuración de Entorno de Pruebas

### Con Docker (Recomendado)

```bash
# 1. Iniciar servicios en modo desarrollo
docker compose up -d

# 2. Verificar que los servicios están corriendo
docker compose ps

# 3. Ejecutar pruebas dentro del contenedor
docker compose exec backend pytest tests/ -v
```

### Local (Sin Docker)

```bash
# 1. Activar entorno virtual
cd backend
source venv/bin/activate

# 2. Instalar dependencias de desarrollo
pip install pytest pytest-asyncio httpx pytest-cov

# 3. Configurar variables de entorno de prueba
export DATABASE_URL="postgresql://ica_user:ica_password@localhost:5432/ica_test"

# 4. Ejecutar pruebas
pytest tests/ -v
```

## 🐋 Ejecutar Pruebas con Docker

### Todas las Pruebas

```bash
docker compose exec backend pytest tests/ -v --cov=app --cov-report=html
```

### Pruebas por Módulo

```bash
# Pruebas de autenticación
docker compose exec backend pytest tests/test_auth.py -v

# Pruebas de declaraciones
docker compose exec backend pytest tests/test_declarations.py -v

# Pruebas de PDF
docker compose exec backend pytest tests/test_pdf.py -v

# Pruebas de administración
docker compose exec backend pytest tests/test_admin.py -v
```

### Pruebas Específicas

```bash
# Una prueba específica
docker compose exec backend pytest tests/test_auth.py::test_register -v

# Con cobertura de código
docker compose exec backend pytest tests/test_auth.py --cov=app.api.endpoints.auth
```

## 🧪 Pruebas Manuales

### 1. Verificar Health Check

```bash
curl http://localhost:8000/health
```

**Respuesta esperada**:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### 2. Verificar Documentación API

Abrir en navegador: http://localhost:8000/api/docs

Deberías ver la interfaz de Swagger UI con todos los endpoints documentados.

### 3. Prueba de Registro de Usuario

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "full_name": "Usuario de Prueba",
    "nit": "1234567890"
  }'
```

**Respuesta esperada**: Código 201 con datos del usuario creado.

### 4. Prueba de Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

**Respuesta esperada**: Código 200 con tokens JWT.

### 5. Prueba de Creación de Declaración

```bash
# Primero obtener el token de acceso del login anterior
TOKEN="<access_token_obtenido>"

curl -X POST http://localhost:8000/api/v1/declarations/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "year": 2024,
    "period": "ANUAL",
    "taxpayer_info": {
      "nit": "1234567890",
      "razon_social": "Empresa XYZ SAS",
      "direccion": "Calle 1 #2-3",
      "municipio": "Bogotá"
    },
    "base_gravable": {
      "row_8": 10000000,
      "row_9": 500000,
      "row_11": 200000
    },
    "activities": [
      {
        "ciiu": "4711",
        "descripcion": "Comercio al por menor",
        "ingresos": 8000000,
        "tarifa": 10
      }
    ]
  }'
```

**Respuesta esperada**: Código 201 con la declaración creada.

### 6. Verificar Base de Datos

```bash
# Conectar a PostgreSQL
docker compose exec postgres psql -U ica_user -d ica_db

# Dentro de psql:
# Ver tablas
\dt

# Ver usuarios
SELECT id, email, full_name, role FROM users;

# Ver declaraciones
SELECT id, number, status, created_at FROM declarations;

# Salir
\q
```

### 7. Verificar Redis

```bash
# Conectar a Redis
docker compose exec redis redis-cli

# Dentro de redis-cli:
# Ver todas las claves
KEYS *

# Ver información del servidor
INFO

# Salir
exit
```

## 📊 Casos de Prueba

### CP-01: Flujo Completo de Declaración

**Objetivo**: Verificar el flujo completo desde registro hasta descarga de PDF.

**Pasos**:

1. **Registrar usuario**
   ```bash
   POST /api/v1/auth/register
   ```

2. **Iniciar sesión**
   ```bash
   POST /api/v1/auth/login
   ```

3. **Crear declaración**
   ```bash
   POST /api/v1/declarations/
   ```

4. **Verificar cálculos automáticos**
   - Verificar que row_10 = row_8 + row_9
   - Verificar que row_16 = row_10 - (row_11 + ... + row_15)
   - Verificar cálculo de impuesto por actividad

5. **Firmar declaración**
   ```bash
   POST /api/v1/declarations/{id}/sign
   ```

6. **Generar PDF**
   ```bash
   POST /api/v1/declarations/{id}/generate-pdf
   ```

7. **Descargar PDF**
   ```bash
   GET /api/v1/declarations/{id}/download-pdf
   ```

**Resultado esperado**: PDF generado correctamente con todos los datos.

---

### CP-02: Validaciones de Seguridad

**Objetivo**: Verificar que las protecciones de seguridad funcionan.

**Pruebas**:

1. **XSS Prevention**
   ```bash
   # Intentar inyectar script en nombre
   POST /api/v1/auth/register
   {
     "full_name": "<script>alert('XSS')</script>",
     ...
   }
   # Verificar que el script se sanitiza
   ```

2. **SQL Injection Prevention**
   ```bash
   # Intentar inyección SQL en login
   POST /api/v1/auth/login
   {
     "email": "admin' OR '1'='1",
     "password": "anything"
   }
   # Debe retornar 401 Unauthorized
   ```

3. **Rate Limiting**
   ```bash
   # Hacer 101 requests en 60 segundos
   for i in {1..101}; do
     curl -X POST http://localhost:8000/api/v1/auth/login \
       -H "Content-Type: application/json" \
       -d '{"email":"test","password":"test"}'
   done
   # Request 101 debe retornar 429 Too Many Requests
   ```

4. **JWT Token Validation**
   ```bash
   # Intentar acceder sin token
   curl http://localhost:8000/api/v1/declarations/
   # Debe retornar 401 Unauthorized
   
   # Intentar con token inválido
   curl -H "Authorization: Bearer invalid_token" \
     http://localhost:8000/api/v1/declarations/
   # Debe retornar 401 Unauthorized
   ```

---

### CP-03: Validaciones de Negocio

**Objetivo**: Verificar que las validaciones de negocio funcionan correctamente.

**Pruebas**:

1. **NIT Inválido**
   ```bash
   POST /api/v1/declarations/
   {
     "taxpayer_info": {
       "nit": "123",  # NIT muy corto
       ...
     }
   }
   # Debe retornar 422 con error de validación
   ```

2. **Monto Negativo**
   ```bash
   POST /api/v1/declarations/
   {
     "base_gravable": {
       "row_8": -1000  # Monto negativo
     }
   }
   # Debe retornar 422 con error de validación
   ```

3. **Editar Declaración Firmada**
   ```bash
   # Firmar declaración
   POST /api/v1/declarations/{id}/sign
   
   # Intentar editar
   PUT /api/v1/declarations/{id}
   # Debe retornar 400 "No se puede editar declaración firmada"
   ```

---

### CP-04: Marca Blanca

**Objetivo**: Verificar configuración de marca blanca por alcaldía.

**Pasos**:

1. **Login como admin de alcaldía**
   ```bash
   POST /api/v1/auth/login
   {
     "email": "admin@alcaldia.gov.co",
     "password": "AdminPass123!"
   }
   ```

2. **Actualizar configuración**
   ```bash
   PUT /api/v1/admin/white-label/{municipality_id}
   {
     "name": "Alcaldía de Bogotá",
     "logo": "data:image/png;base64,...",
     "primary_color": "#003366",
     "secondary_color": "#FFCC00"
   }
   ```

3. **Generar PDF con nueva marca**
   ```bash
   POST /api/v1/declarations/{id}/generate-pdf
   ```

4. **Verificar que PDF tiene logo y colores correctos**

---

### CP-05: Performance

**Objetivo**: Verificar que el sistema cumple con requisitos de performance.

**Métricas objetivo**:
- Tiempo de respuesta < 200ms (promedio)
- 100 usuarios concurrentes
- < 1% tasa de error

**Herramienta**: Apache Bench o Locust

```bash
# Con Apache Bench
ab -n 1000 -c 100 http://localhost:8000/health

# Con Locust (requiere instalación)
pip install locust
locust -f tests/load_test.py --host=http://localhost:8000
```

---

## 🔍 Verificación de Logs

### Ver Logs de la Aplicación

```bash
# Todos los servicios
docker compose logs

# Solo backend
docker compose logs backend

# En tiempo real
docker compose logs -f backend

# Últimas 100 líneas
docker compose logs --tail=100 backend
```

### Verificar Logs de Auditoría

Los logs de auditoría registran todas las operaciones críticas:

```bash
# Dentro del contenedor
docker compose exec backend cat /var/log/ica/audit.log

# O ver en base de datos
docker compose exec postgres psql -U ica_user -d ica_db \
  -c "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10;"
```

---

## 📈 Cobertura de Código

### Generar Reporte de Cobertura

```bash
# Ejecutar pruebas con cobertura
docker compose exec backend pytest tests/ --cov=app --cov-report=html --cov-report=term

# Ver reporte en terminal
docker compose exec backend pytest tests/ --cov=app --cov-report=term-missing

# Copiar reporte HTML al host
docker compose cp backend:/app/htmlcov ./htmlcov

# Abrir en navegador
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

**Objetivo de cobertura**: > 80%

---

## ✅ Checklist de Verificación

Antes de considerar el sistema listo:

- [ ] Health check responde correctamente
- [ ] Documentación API accesible en /api/docs
- [ ] Registro de usuario funciona
- [ ] Login retorna tokens JWT válidos
- [ ] Creación de declaración funciona
- [ ] Cálculos automáticos son correctos
- [ ] Firma digital se almacena correctamente
- [ ] PDF se genera con logo de alcaldía
- [ ] PDF se puede descargar
- [ ] Rate limiting funciona
- [ ] Sanitización XSS funciona
- [ ] Protección SQL Injection funciona
- [ ] Tokens inválidos son rechazados
- [ ] Logs de auditoría se registran
- [ ] Base de datos persiste datos correctamente
- [ ] Redis funciona (si está configurado)
- [ ] Todos los tests unitarios pasan
- [ ] Cobertura de código > 80%

---

## 🆘 Troubleshooting de Pruebas

### Problema: Tests fallan por timeout

**Solución**:
```bash
# Aumentar timeout en pytest
docker compose exec backend pytest tests/ -v --timeout=60
```

### Problema: Base de datos no está lista

**Solución**:
```bash
# Esperar a que PostgreSQL esté listo
docker compose exec postgres pg_isready -U ica_user

# Reiniciar servicios con depends_on
docker compose down && docker compose up -d
```

### Problema: Puerto en uso

**Solución**:
```bash
# Verificar qué está usando el puerto
sudo lsof -i :8000

# Cambiar puerto en docker-compose.yml
ports:
  - "9000:8000"  # Usar puerto 9000 externamente
```

---

## 📚 Recursos Adicionales

- [Documentación de pytest](https://docs.pytest.org/)
- [Testing FastAPI](https://fastapi.tiangolo.com/tutorial/testing/)
- [Docker Testing Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

**¡Sistema listo para pruebas! 🎉**
