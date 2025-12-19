# 📚 Documentación Completa del Sistema ICA

## Sistema de Formulario Único Nacional de Declaración y Pago del Impuesto de Industria y Comercio

---

## Índice

1. [Descripción General](#1-descripción-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Casos de Uso](#3-casos-de-uso)
4. [Pruebas del Sistema](#4-pruebas-del-sistema)
5. [Implementaciones de Seguridad](#5-implementaciones-de-seguridad)
6. [Manual de Usuario](#6-manual-de-usuario)
7. [API Reference](#7-api-reference)

---

## 1. Descripción General

### 1.1 Propósito del Sistema

El Sistema ICA es una plataforma web institucional diseñada para el diligenciamiento del Formulario Único Nacional de Declaración y Pago del Impuesto de Industria y Comercio (ICA). El sistema permite a los contribuyentes:

- Registrarse y autenticarse de forma segura
- Diligenciar el formulario ICA completo
- Calcular automáticamente el impuesto según normativa
- Firmar digitalmente sus declaraciones
- Generar y descargar PDF oficial del formulario
- Gestionar múltiples declaraciones

### 1.2 Características Principales

#### ✅ Funcionalidades Implementadas

1. **Autenticación y Autorización**
   - Sistema JWT (JSON Web Tokens)
   - Tokens de acceso y refresco
   - Roles de usuario (Declarante, Admin Alcaldía, Admin Sistema)
   - Hash de contraseñas con Argon2

2. **Gestión de Formularios ICA**
   - Formulario completo con todas las secciones (A-G)
   - Cálculo automático de renglones según fórmulas oficiales
   - Validación de datos según normativa
   - Guardado de borradores
   - Historial de declaraciones

3. **Firma Digital**
   - Canvas HTML5 para firma manuscrita
   - Almacenamiento seguro de firmas
   - Validación de firma antes de envío

4. **Generación de PDF**
   - PDF institucional con marca de agua
   - Logo personalizado por alcaldía
   - Almacenamiento organizado (año/municipio/usuario)
   - Descarga segura de documentos

5. **Marca Blanca (White Label)**
   - Personalización por alcaldía
   - Logos, colores, información institucional
   - Configuración dinámica sin código

6. **Seguridad by Design**
   - Protección contra XSS, CSRF, SQL Injection
   - Rate limiting
   - Headers de seguridad
   - Logs de auditoría
   - Sanitización de inputs

### 1.3 Stack Tecnológico

#### Backend
- **Framework**: FastAPI 0.109+
- **Lenguaje**: Python 3.10+
- **Base de Datos**: PostgreSQL 14+
- **Cache**: Redis 7+ (opcional)
- **ORM**: SQLAlchemy 2.0+
- **Validación**: Pydantic 2.6+
- **PDF**: ReportLab 4.1+
- **Seguridad**: python-jose, passlib, argon2-cffi

#### Frontend
- **HTML5**: Estructura semántica
- **CSS3**: Diseño responsivo
- **JavaScript**: Vanilla JS (sin frameworks)
- **Canvas API**: Para firma digital

#### Infraestructura
- **Servidor**: Uvicorn con workers
- **Proxy**: Nginx (recomendado)
- **Gestión de Procesos**: Supervisor/systemd
- **Contenedores**: Docker + Docker Compose

---

## 2. Arquitectura del Sistema

### 2.1 Arquitectura General

```
┌─────────────────────────────────────────────────────────────┐
│                        USUARIO FINAL                         │
│                      (Navegador Web)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTPS
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                         NGINX                                │
│                    (Proxy Reverso)                           │
│    • SSL/TLS Termination                                     │
│    • Load Balancing                                          │
│    • Static Files                                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────┐              ┌──────────────┐
│   Frontend   │              │   Backend    │
│   (Static)   │              │   FastAPI    │
│              │              │              │
│ • HTML       │              │ • REST API   │
│ • CSS        │              │ • Business   │
│ • JavaScript │              │   Logic      │
└──────────────┘              │ • Validation │
                              └──────┬───────┘
                                     │
                   ┌─────────────────┼─────────────────┐
                   │                 │                 │
                   ▼                 ▼                 ▼
           ┌──────────────┐  ┌──────────────┐ ┌──────────────┐
           │  PostgreSQL  │  │    Redis     │ │  File System │
           │              │  │              │ │              │
           │ • Users      │  │ • Cache      │ │ • PDFs       │
           │ • Declar.    │  │ • Sessions   │ │ • Assets     │
           │ • Config     │  │ • Rate Limit │ │ • Logos      │
           └──────────────┘  └──────────────┘ └──────────────┘
```

### 2.2 Estructura de Directorios

```
ICA/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py           # Autenticación
│   │   │   │   ├── declarations.py   # CRUD declaraciones
│   │   │   │   └── admin.py          # Administración
│   │   │   └── middleware/
│   │   │       └── security.py       # Seguridad
│   │   ├── core/
│   │   │   ├── config.py             # Configuración
│   │   │   └── security.py           # JWT, hashing
│   │   ├── db/
│   │   │   └── database.py           # Conexión DB
│   │   ├── models/
│   │   │   └── models.py             # Modelos ORM
│   │   ├── schemas/
│   │   │   └── schemas.py            # Validación
│   │   ├── services/
│   │   │   ├── calculation_engine.py # Motor cálculos
│   │   │   └── pdf_generator.py      # Generación PDF
│   │   ├── utils/
│   │   │   └── validators.py         # Validaciones
│   │   └── main.py                   # Aplicación principal
│   ├── tests/                        # Tests unitarios
│   └── requirements.txt              # Dependencias
├── frontend/
│   ├── css/
│   │   └── styles.css                # Estilos
│   ├── js/
│   │   ├── api.js                    # Cliente API
│   │   ├── ica-form.js               # Lógica formulario
│   │   └── signature.js              # Firma digital
│   └── templates/
│       ├── login.html                # Login
│       ├── dashboard.html            # Dashboard
│       ├── form.html                 # Formulario ICA
│       └── admin.html                # Panel admin
├── docs/
│   ├── DEPLOYMENT.md                 # Guía despliegue
│   ├── DOCKER.md                     # Guía Docker
│   └── DOCUMENTACION_COMPLETA.md     # Este archivo
├── Documents/
│   └── formulario-ICA.md             # Especificación
├── Dockerfile                        # Imagen Docker
├── docker-compose.yml                # Orquestación
└── README.md                         # Readme principal
```

### 2.3 Flujo de Datos

#### Flujo de Autenticación

```
Usuario → POST /api/v1/auth/login
    ↓
Validar credenciales (email + password)
    ↓
Verificar hash Argon2
    ↓
Generar JWT (access_token + refresh_token)
    ↓
← Retornar tokens
```

#### Flujo de Creación de Declaración

```
Usuario autenticado → POST /api/v1/declarations/
    ↓
Validar token JWT
    ↓
Validar datos formulario (Pydantic)
    ↓
Calcular renglones automáticos
    ↓
Guardar en base de datos
    ↓
← Retornar declaración creada
```

#### Flujo de Firma y Generación PDF

```
Usuario → POST /api/v1/declarations/{id}/sign
    ↓
Validar firma digital
    ↓
Actualizar estado: "FIRMADA"
    ↓
POST /api/v1/declarations/{id}/generate-pdf
    ↓
Generar PDF con ReportLab
    ↓
Guardar en /var/ica/pdfs/{año}/{municipio}/{user_id}/
    ↓
← Retornar URL de descarga
```

---

## 3. Casos de Uso

### 3.1 Actores del Sistema

1. **Contribuyente/Declarante**: Usuario que diligencia formularios ICA
2. **Administrador de Alcaldía**: Gestiona configuración del municipio
3. **Administrador del Sistema**: Control total del sistema

### 3.2 Casos de Uso Principales

#### CU-01: Registro de Usuario

**Actor**: Contribuyente  
**Precondición**: Usuario no registrado  
**Flujo Principal**:
1. Usuario accede a la página de registro
2. Ingresa email, contraseña, nombre completo, NIT/documento
3. Sistema valida formato de datos
4. Sistema hashea contraseña con Argon2
5. Sistema crea usuario con rol "DECLARANTE"
6. Sistema envía confirmación

**Postcondición**: Usuario registrado y puede iniciar sesión

**Flujos Alternativos**:
- 3a. Email ya existe → Error "Email ya registrado"
- 3b. Contraseña débil → Error "Contraseña debe tener mínimo 8 caracteres"
- 3c. NIT inválido → Error "NIT no válido"

---

#### CU-02: Inicio de Sesión

**Actor**: Cualquier usuario registrado  
**Precondición**: Usuario registrado  
**Flujo Principal**:
1. Usuario ingresa email y contraseña
2. Sistema valida credenciales
3. Sistema verifica hash Argon2
4. Sistema genera JWT tokens
5. Sistema retorna access_token y refresh_token
6. Usuario redirigido a dashboard

**Postcondición**: Usuario autenticado con sesión activa

**Flujos Alternativos**:
- 3a. Credenciales incorrectas → Error "Credenciales inválidas"
- 3b. Usuario bloqueado → Error "Usuario bloqueado"
- 3c. Rate limit excedido → Error "Demasiados intentos"

---

#### CU-03: Crear Nueva Declaración ICA

**Actor**: Contribuyente  
**Precondición**: Usuario autenticado  
**Flujo Principal**:
1. Usuario accede a "Nueva Declaración"
2. Sistema muestra formulario vacío con secciones A-G
3. Usuario diligencia Sección A (Información Contribuyente)
   - NIT, razón social, dirección, municipio, etc.
4. Usuario diligencia Sección B (Base Gravable)
   - Renglones 8-16: ingresos, devoluciones, descuentos
   - Sistema calcula automáticamente totales
5. Usuario diligencia Sección C (Actividades Gravadas)
   - Código CIIU, descripción, tarifa por mil
   - Ingresos por actividad
6. Sistema calcula Sección D (Liquidación)
   - Renglones 30-33: impuesto por actividad
   - Total impuesto
7. Usuario diligencia Sección E (Descuentos y Anticipos)
8. Sistema calcula Sección F (Total a Pagar)
9. Usuario guarda borrador
10. Sistema almacena declaración con estado "BORRADOR"

**Postcondición**: Declaración creada en estado BORRADOR

**Flujos Alternativos**:
- 3a. Datos inválidos → Mostrar errores de validación
- 6a. Error en cálculos → Registrar log y notificar
- 9a. Usuario cierra sin guardar → Confirmar pérdida de datos

---

#### CU-04: Firmar Declaración Digitalmente

**Actor**: Contribuyente  
**Precondición**: Declaración en estado BORRADOR completa  
**Flujo Principal**:
1. Usuario accede a declaración borrador
2. Sistema valida que todos los campos obligatorios estén completos
3. Sistema muestra Sección G (Firma y Responsabilidad)
4. Usuario lee declaración de responsabilidad
5. Usuario dibuja firma en canvas HTML5
6. Usuario confirma firma
7. Sistema convierte firma a imagen PNG base64
8. Sistema almacena firma
9. Sistema actualiza estado a "FIRMADA"
10. Sistema registra timestamp de firma

**Postcondición**: Declaración firmada digitalmente

**Flujos Alternativos**:
- 2a. Campos incompletos → Error "Debe completar todos los campos"
- 5a. Usuario cancela firma → Volver a paso 3
- 7a. Error al procesar firma → Error técnico

---

#### CU-05: Generar PDF Oficial

**Actor**: Contribuyente  
**Precondición**: Declaración FIRMADA  
**Flujo Principal**:
1. Usuario solicita generar PDF
2. Sistema valida que declaración esté firmada
3. Sistema obtiene configuración de marca blanca del municipio
4. Sistema genera PDF con ReportLab
   - Header con logo de alcaldía
   - Datos del formulario completo (secciones A-F)
   - Firma digital (Sección G)
   - Marca de agua institucional
   - Número de radicado único
   - Timestamp de generación
5. Sistema guarda PDF en /var/ica/pdfs/{año}/{municipio}/{user_id}/
6. Sistema actualiza estado a "PRESENTADA"
7. Sistema retorna URL de descarga

**Postcondición**: PDF generado y disponible para descarga

**Flujos Alternativos**:
- 2a. No está firmada → Error "Debe firmar primero"
- 4a. Error generando PDF → Registrar error y reintentar
- 5a. Error de almacenamiento → Notificar admin

---

#### CU-06: Descargar PDF de Declaración

**Actor**: Contribuyente  
**Precondición**: PDF generado  
**Flujo Principal**:
1. Usuario accede a historial de declaraciones
2. Usuario selecciona declaración PRESENTADA
3. Usuario hace clic en "Descargar PDF"
4. Sistema valida permisos de usuario
5. Sistema obtiene ruta del PDF
6. Sistema retorna archivo PDF
7. Navegador descarga archivo

**Postcondición**: Usuario tiene PDF en su dispositivo

**Flujos Alternativos**:
- 4a. Usuario sin permisos → Error "No autorizado"
- 5a. Archivo no existe → Error "PDF no encontrado"
- 6a. Error de red → Reintentar descarga

---

#### CU-07: Configurar Marca Blanca (Admin Alcaldía)

**Actor**: Administrador de Alcaldía  
**Precondición**: Usuario con rol ADMIN_ALCALDIA autenticado  
**Flujo Principal**:
1. Admin accede a panel de administración
2. Sistema muestra configuración actual
3. Admin actualiza:
   - Nombre de la alcaldía
   - Logo institucional (upload)
   - Colores corporativos
   - Información de contacto
   - Tarifas ICA por actividad CIIU
4. Admin guarda cambios
5. Sistema valida datos
6. Sistema actualiza configuración en BD
7. Sistema actualiza assets en filesystem
8. Sistema aplica cambios inmediatamente

**Postcondición**: Marca blanca actualizada

**Flujos Alternativos**:
- 5a. Logo muy grande → Error "Máximo 5MB"
- 5b. Formato inválido → Error "Solo PNG, JPG"
- 6a. Error de BD → Rollback y notificar

---

#### CU-08: Ver Historial de Declaraciones

**Actor**: Contribuyente  
**Precondición**: Usuario autenticado  
**Flujo Principal**:
1. Usuario accede a "Mis Declaraciones"
2. Sistema obtiene declaraciones del usuario
3. Sistema muestra lista paginada con:
   - Número de declaración
   - Año gravable
   - Estado (BORRADOR, FIRMADA, PRESENTADA)
   - Fecha de creación
   - Fecha de presentación
   - Total a pagar
4. Usuario puede filtrar por año, estado
5. Usuario puede buscar por número

**Postcondición**: Usuario visualiza su historial

**Flujos Alternativos**:
- 2a. Sin declaraciones → Mostrar mensaje vacío
- 4a. Sin resultados en filtro → Mensaje informativo

---

#### CU-09: Editar Declaración Borrador

**Actor**: Contribuyente  
**Precondición**: Declaración en estado BORRADOR  
**Flujo Principal**:
1. Usuario selecciona declaración borrador
2. Sistema carga datos existentes
3. Sistema muestra formulario prellenado
4. Usuario modifica campos necesarios
5. Sistema recalcula automáticamente
6. Usuario guarda cambios
7. Sistema valida y actualiza

**Postcondición**: Declaración actualizada

**Flujos Alternativos**:
- 1a. Declaración firmada → Error "No se puede editar"
- 5a. Datos inválidos → Mostrar errores
- 7a. Conflicto de versión → Notificar y recargar

---

#### CU-10: Recuperar Contraseña

**Actor**: Cualquier usuario  
**Precondición**: Usuario registrado  
**Flujo Principal**:
1. Usuario hace clic en "Olvidé mi contraseña"
2. Usuario ingresa email
3. Sistema valida que email existe
4. Sistema genera token de recuperación
5. Sistema envía email con link
6. Usuario hace clic en link
7. Sistema valida token (no expirado)
8. Usuario ingresa nueva contraseña
9. Sistema valida fortaleza
10. Sistema hashea con Argon2
11. Sistema actualiza contraseña
12. Sistema invalida token usado

**Postcondición**: Contraseña actualizada

**Flujos Alternativos**:
- 3a. Email no existe → Mensaje genérico (seguridad)
- 7a. Token expirado → Solicitar nuevo
- 9a. Contraseña débil → Mostrar requisitos

---

### 3.3 Diagrama de Casos de Uso

```
                    Sistema ICA
    ┌───────────────────────────────────────┐
    │                                       │
    │  (CU-01) Registro                     │
    │  (CU-02) Inicio Sesión                │
    │  (CU-03) Crear Declaración            │
    │  (CU-04) Firmar Declaración      │◄───┼─── Contribuyente
    │  (CU-05) Generar PDF                  │
    │  (CU-06) Descargar PDF                │
    │  (CU-08) Ver Historial                │
    │  (CU-09) Editar Borrador              │
    │  (CU-10) Recuperar Contraseña         │
    │                                       │
    │  (CU-07) Configurar Marca Blanca │◄───┼─── Admin Alcaldía
    │                                       │
    └───────────────────────────────────────┘
```

---

## 4. Pruebas del Sistema

### 4.1 Estrategia de Pruebas

El sistema implementa pruebas en múltiples niveles:

1. **Pruebas Unitarias**: Funciones individuales
2. **Pruebas de Integración**: Interacción entre componentes
3. **Pruebas de API**: Endpoints REST
4. **Pruebas de Seguridad**: Vulnerabilidades
5. **Pruebas de Carga**: Performance

### 4.2 Casos de Prueba por Caso de Uso

#### TC-01: Pruebas de Registro (CU-01)

| ID | Descripción | Entrada | Resultado Esperado | Estado |
|----|-------------|---------|-------------------|--------|
| TC-01-01 | Registro exitoso | Email válido, contraseña fuerte, datos completos | Usuario creado, código 201 | ✅ |
| TC-01-02 | Email duplicado | Email existente | Error "Email ya registrado", código 400 | ✅ |
| TC-01-03 | Contraseña débil | Contraseña < 8 caracteres | Error validación, código 422 | ✅ |
| TC-01-04 | Email inválido | "invalid-email" | Error formato email, código 422 | ✅ |
| TC-01-05 | NIT inválido | NIT con formato incorrecto | Error validación NIT, código 422 | ✅ |
| TC-01-06 | Campos faltantes | Sin email | Error campo requerido, código 422 | ✅ |
| TC-01-07 | SQL Injection | Email con "'; DROP TABLE--" | Sanitizado, no ejecuta | ✅ |
| TC-01-08 | XSS en nombre | Nombre con "<script>" | Sanitizado, almacenado seguro | ✅ |

**Comando de prueba**:
```bash
docker compose exec backend pytest tests/test_auth.py::test_register -v
```

---

#### TC-02: Pruebas de Autenticación (CU-02)

| ID | Descripción | Entrada | Resultado Esperado | Estado |
|----|-------------|---------|-------------------|--------|
| TC-02-01 | Login exitoso | Credenciales correctas | JWT tokens, código 200 | ✅ |
| TC-02-02 | Credenciales incorrectas | Password incorrecto | Error "Inválidas", código 401 | ✅ |
| TC-02-03 | Usuario no existe | Email no registrado | Error "Inválidas", código 401 | ✅ |
| TC-02-04 | Rate limiting | 100+ intentos/minuto | Error 429 Too Many Requests | ✅ |
| TC-02-05 | Token expirado | Token > 60 minutos | Error 401 Unauthorized | ✅ |
| TC-02-06 | Token inválido | Token modificado | Error 401 signature invalid | ✅ |
| TC-02-07 | Refresh token | Token refresco válido | Nuevos tokens, código 200 | ✅ |
| TC-02-08 | Brute force | Múltiples intentos fallidos | Cuenta bloqueada temporal | ✅ |

**Comando de prueba**:
```bash
docker compose exec backend pytest tests/test_auth.py::test_login -v
```

---

#### TC-03: Pruebas de Declaración (CU-03, CU-09)

| ID | Descripción | Entrada | Resultado Esperado | Estado |
|----|-------------|---------|-------------------|--------|
| TC-03-01 | Crear declaración válida | Datos completos válidos | Declaración creada, código 201 | ✅ |
| TC-03-02 | Sin autenticación | Sin token JWT | Error 401 Unauthorized | ✅ |
| TC-03-03 | Cálculo renglón 10 | R8=1000, R9=500 | R10=1500 automático | ✅ |
| TC-03-04 | Cálculo renglón 16 | R10=10000, R11-15=2000 | R16=8000 automático | ✅ |
| TC-03-05 | Cálculo impuesto | Ingreso=10000, tarifa=10/1000 | Impuesto=100 | ✅ |
| TC-03-06 | NIT inválido | NIT formato incorrecto | Error validación, código 422 | ✅ |
| TC-03-07 | Monto negativo | Renglón con valor < 0 | Error validación, código 422 | ✅ |
| TC-03-08 | Guardar borrador | Estado BORRADOR | Guardado, permite edición | ✅ |
| TC-03-09 | Editar borrador | Actualizar campo | Campo actualizado, código 200 | ✅ |
| TC-03-10 | Editar firmada | Actualizar declaración firmada | Error "No editable", código 400 | ✅ |

**Comando de prueba**:
```bash
docker compose exec backend pytest tests/test_declarations.py -v
```

---

#### TC-04: Pruebas de Firma Digital (CU-04)

| ID | Descripción | Entrada | Resultado Esperado | Estado |
|----|-------------|---------|-------------------|--------|
| TC-04-01 | Firma válida | Imagen base64 PNG | Firmada, estado FIRMADA | ✅ |
| TC-04-02 | Sin firma | Firma vacía | Error "Firma requerida", código 422 | ✅ |
| TC-04-03 | Formato inválido | Imagen JPG/GIF | Error formato, código 422 | ✅ |
| TC-04-04 | Firma muy grande | > 5MB | Error tamaño, código 422 | ✅ |
| TC-04-05 | Campos incompletos | Falta datos obligatorios | Error "Completar campos", código 400 | ✅ |
| TC-04-06 | Firmar ya firmada | Declaración en estado FIRMADA | Error "Ya firmada", código 400 | ✅ |

**Comando de prueba**:
```bash
docker compose exec backend pytest tests/test_signature.py -v
```

---

#### TC-05: Pruebas de Generación PDF (CU-05)

| ID | Descripción | Entrada | Resultado Esperado | Estado |
|----|-------------|---------|-------------------|--------|
| TC-05-01 | PDF válido | Declaración firmada | PDF generado, código 200 | ✅ |
| TC-05-02 | Sin firma | Declaración borrador | Error "Firmar primero", código 400 | ✅ |
| TC-05-03 | Logo alcaldía | Con configuración marca blanca | PDF con logo incluido | ✅ |
| TC-05-04 | Sin logo | Sin marca blanca | PDF con logo por defecto | ✅ |
| TC-05-05 | Ruta organizada | Año 2024, municipio X, user 1 | /2024/X/1/declaracion.pdf | ✅ |
| TC-05-06 | Timestamp | Verificar fecha generación | Fecha correcta en PDF | ✅ |
| TC-05-07 | Número radicado | Verificar único | Radicado único generado | ✅ |

**Comando de prueba**:
```bash
docker compose exec backend pytest tests/test_pdf.py -v
```

---

#### TC-06: Pruebas de Marca Blanca (CU-07)

| ID | Descripción | Entrada | Resultado Esperado | Estado |
|----|-------------|---------|-------------------|--------|
| TC-06-01 | Config válida | Datos completos | Actualizado, código 200 | ✅ |
| TC-06-02 | Sin permisos | Usuario declarante | Error 403 Forbidden | ✅ |
| TC-06-03 | Logo válido | PNG 2MB | Logo actualizado | ✅ |
| TC-06-04 | Logo grande | PNG 10MB | Error "Máx 5MB", código 422 | ✅ |
| TC-06-05 | Formato inválido | EXE file | Error formato, código 422 | ✅ |
| TC-06-06 | Color inválido | "#ZZZZZZ" | Error formato hex, código 422 | ✅ |

**Comando de prueba**:
```bash
docker compose exec backend pytest tests/test_admin.py -v
```

---

### 4.3 Pruebas de Seguridad

#### TS-01: Protección XSS

```python
def test_xss_protection():
    """Verificar sanitización contra XSS"""
    payload = {
        "name": "<script>alert('XSS')</script>",
        "email": "test@test.com"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    # Verificar que script está sanitizado
    assert "<script>" not in response.json()["name"]
```

#### TS-02: Protección SQL Injection

```python
def test_sql_injection():
    """Verificar protección contra SQL Injection"""
    payload = {
        "email": "admin' OR '1'='1",
        "password": "password"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    # No debe autenticar
    assert response.status_code == 401
```

#### TS-03: Protección CSRF

```python
def test_csrf_protection():
    """Verificar tokens CSRF"""
    response = client.post("/api/v1/declarations/", 
                          headers={"X-CSRF-Token": "invalid"})
    assert response.status_code == 403
```

#### TS-04: Rate Limiting

```python
def test_rate_limiting():
    """Verificar límite de peticiones"""
    for i in range(101):
        response = client.post("/api/v1/auth/login", 
                              json={"email": "test", "password": "test"})
    # Request 101 debe ser bloqueada
    assert response.status_code == 429
```

### 4.4 Pruebas de Carga

```bash
# Instalar locust
pip install locust

# Ejecutar prueba de carga
locust -f tests/load_test.py --host=http://localhost:8000
```

**Métricas objetivo**:
- 100 usuarios concurrentes
- < 200ms tiempo de respuesta promedio
- < 1% tasa de error
- 1000+ requests/segundo

### 4.5 Cobertura de Código

```bash
# Ejecutar con cobertura
docker compose exec backend pytest --cov=app --cov-report=html

# Ver reporte
open htmlcov/index.html
```

**Objetivo**: > 80% cobertura

---

## 5. Implementaciones de Seguridad

### 5.1 Resumen Ejecutivo de Seguridad

El Sistema ICA ha sido diseñado con **Security by Design** como principio fundamental. Todas las funcionalidades implementan múltiples capas de seguridad para proteger:

- **Datos de contribuyentes** (información personal y financiera)
- **Integridad de declaraciones tributarias**
- **Autenticidad de documentos oficiales**
- **Disponibilidad del servicio**
- **Confidencialidad de información institucional**

### 5.2 Arquitectura de Seguridad

```
┌─────────────────────────────────────────────────────────┐
│              CAPAS DE SEGURIDAD                         │
├─────────────────────────────────────────────────────────┤
│ 1. Infraestructura                                      │
│    • Firewall                                           │
│    • SSL/TLS (HTTPS obligatorio)                        │
│    • Aislamiento de red (Docker)                        │
├─────────────────────────────────────────────────────────┤
│ 2. Aplicación                                           │
│    • Headers de seguridad                               │
│    • Rate limiting                                      │
│    • Input sanitization                                 │
│    • Output encoding                                    │
├─────────────────────────────────────────────────────────┤
│ 3. Autenticación y Autorización                         │
│    • JWT tokens                                         │
│    • Argon2 password hashing                            │
│    • RBAC (Role-Based Access Control)                   │
│    • Session management                                 │
├─────────────────────────────────────────────────────────┤
│ 4. Datos                                                │
│    • Cifrado en tránsito (TLS)                          │
│    • Cifrado en reposo (opcional)                       │
│    • Validación de datos (Pydantic)                     │
│    • Prepared statements (SQLAlchemy)                   │
├─────────────────────────────────────────────────────────┤
│ 5. Monitoreo y Auditoría                                │
│    • Logs de acceso                                     │
│    • Logs de auditoría                                  │
│    • Alertas de seguridad                               │
│    • Análisis de anomalías                              │
└─────────────────────────────────────────────────────────┘
```

### 5.3 Controles de Seguridad Implementados

#### 5.3.1 Autenticación y Autorización

**JWT (JSON Web Tokens)**
- ✅ Tokens firmados con algoritmo HS256
- ✅ Access tokens con expiración de 60 minutos
- ✅ Refresh tokens con expiración de 7 días
- ✅ Validación de firma en cada request
- ✅ Blacklist de tokens revocados

**Password Hashing - Argon2**
```python
# Implementación
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    argon2__time_cost=2,
    argon2__memory_cost=65536,
    argon2__parallelism=1
)

# Características:
# - Argon2id (ganador Password Hashing Competition 2015)
# - Resistente a ataques GPU/ASIC
# - Ajustable computacionalmente
# - Salt automático único por contraseña
```

**Control de Acceso Basado en Roles (RBAC)**
```python
class UserRole(str, Enum):
    DECLARANTE = "declarante"           # Usuario normal
    ADMIN_ALCALDIA = "admin_alcaldia"   # Admin municipal
    ADMIN_SISTEMA = "admin_sistema"     # Super admin

# Decoradores de autorización
@require_role(UserRole.ADMIN_ALCALDIA)
def update_white_label():
    pass
```

#### 5.3.2 Protección de Aplicación Web

**Headers de Seguridad**
```python
SecurityHeadersMiddleware implementa:

X-Content-Type-Options: nosniff
    → Previene MIME type sniffing

X-Frame-Options: DENY
    → Previene clickjacking

X-XSS-Protection: 1; mode=block
    → Habilita filtro XSS del navegador

Strict-Transport-Security: max-age=31536000
    → Fuerza HTTPS por 1 año

Content-Security-Policy: default-src 'self'
    → Controla fuentes de contenido

Referrer-Policy: strict-origin-when-cross-origin
    → Controla información de referrer

Permissions-Policy: geolocation=(), microphone=()
    → Deshabilita APIs innecesarias
```

**Rate Limiting**
```python
RateLimitMiddleware implementa:

Límites:
- 100 requests por minuto por IP
- Ventanas deslizantes
- Almacenamiento en Redis

Previene:
- Ataques de fuerza bruta
- DDoS distribuidos
- Scraping abusivo
```

**Sanitización de Inputs**
```python
InputSanitizationMiddleware:

def sanitize_html(text: str) -> str:
    """Elimina HTML/scripts peligrosos"""
    return bleach.clean(text, tags=[], strip=True)

Protege contra:
- XSS (Cross-Site Scripting)
- HTML Injection
- JavaScript Injection
```

**Validación de Datos - Pydantic**
```python
class DeclarationCreate(BaseModel):
    nit: str = Field(..., regex=r'^\d{9,10}$')
    razon_social: str = Field(..., min_length=3, max_length=200)
    total_ingresos: Decimal = Field(..., ge=0, max_digits=15)
    
    @validator('nit')
    def validate_nit(cls, v):
        # Validación dígito verificador NIT Colombia
        return validate_colombian_nit(v)
```

#### 5.3.3 Protección de Base de Datos

**SQL Injection Prevention**
```python
# SQLAlchemy ORM con prepared statements
from sqlalchemy import select

# ✅ SEGURO - Parametrizado automáticamente
stmt = select(User).where(User.email == user_email)
user = session.scalar(stmt)

# ❌ NUNCA hacer esto:
# query = f"SELECT * FROM users WHERE email = '{user_email}'"
```

**Cifrado de Datos Sensibles**
```python
# Opcional - Cifrado a nivel de columna
from cryptography.fernet import Fernet

class EncryptedField(TypeDecorator):
    impl = String
    
    def process_bind_param(self, value, dialect):
        if value:
            return fernet.encrypt(value.encode())
        return value
    
    def process_result_value(self, value, dialect):
        if value:
            return fernet.decrypt(value).decode()
        return value
```

**Backups Seguros**
```bash
# Backup cifrado
pg_dump -U ica_user ica_db | \
  gpg --symmetric --cipher-algo AES256 > \
  backup_$(date +%Y%m%d).sql.gpg
```

#### 5.3.4 Protección de Archivos

**Validación de Uploads**
```python
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_upload(file):
    # Verificar extensión
    if not allowed_file(file.filename):
        raise ValueError("Formato no permitido")
    
    # Verificar tamaño
    if len(file.read()) > MAX_FILE_SIZE:
        raise ValueError("Archivo muy grande")
    
    # Verificar contenido (magic numbers)
    if not is_valid_image(file):
        raise ValueError("Archivo corrupto")
```

**Almacenamiento Seguro**
```python
# Generación de nombres únicos
import uuid

def save_pdf(declaration_id: int, year: int, 
             municipality: str, user_id: int):
    filename = f"{uuid.uuid4()}.pdf"
    path = f"/var/ica/pdfs/{year}/{municipality}/{user_id}"
    
    # Crear directorio con permisos restrictivos
    os.makedirs(path, mode=0o750, exist_ok=True)
    
    # Guardar con permisos de solo lectura para owner
    full_path = os.path.join(path, filename)
    with open(full_path, 'wb', opener=secure_opener) as f:
        f.write(pdf_content)
```

#### 5.3.5 Logs y Auditoría

**Audit Log Middleware**
```python
class AuditLogMiddleware:
    """Registra todas las operaciones críticas"""
    
    async def __call__(self, request, call_next):
        # Extraer información
        user_id = get_current_user_id(request)
        ip = request.client.host
        endpoint = request.url.path
        method = request.method
        
        # Registrar en BD
        log_entry = AuditLog(
            user_id=user_id,
            ip_address=ip,
            endpoint=endpoint,
            method=method,
            timestamp=datetime.utcnow()
        )
        db.add(log_entry)
        
        # Alertar si actividad sospechosa
        if is_suspicious(log_entry):
            send_alert(log_entry)
```

**Logs Estructurados**
```python
import logging
import json

logger = logging.getLogger("ica")

def log_security_event(event_type, user_id, details):
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": event_type,
        "user_id": user_id,
        "details": details,
        "severity": "HIGH" if event_type in CRITICAL_EVENTS else "INFO"
    }
    logger.warning(json.dumps(log_data))
```

### 5.4 Gestión de Vulnerabilidades

#### Proceso de Actualización

1. **Monitoreo de CVEs**
   - Suscripción a listas de seguridad
   - Escaneo semanal de dependencias
   - GitHub Security Alerts habilitado

2. **Actualización de Dependencias**
```bash
# Verificar vulnerabilidades
pip-audit

# Actualizar paquetes
pip install --upgrade pip-audit
pip install -r requirements.txt --upgrade
```

3. **Análisis Estático**
```bash
# Bandit - Security linter
bandit -r app/

# Safety - Dependencias vulnerables
safety check
```

#### Vulnerabilidades Conocidas y Mitigadas

| CVE | Descripción | Mitigación | Estado |
|-----|-------------|------------ |--------|
| N/A | Path Traversal en descarga PDF | Validación estricta de paths | ✅ |
| N/A | XSS en campos de texto | Sanitización con bleach | ✅ |
| N/A | CSRF en formularios | Tokens CSRF | ✅ |
| N/A | Timing attacks en login | Respuestas constantes | ✅ |
| N/A | Session fixation | Regeneración de tokens | ✅ |

### 5.5 Compliance y Normativa

#### Ley de Protección de Datos (Colombia)

**Ley 1581 de 2012 - Habeas Data**

Cumplimiento:
- ✅ Consentimiento informado al registrarse
- ✅ Política de privacidad visible
- ✅ Derecho de acceso a datos personales
- ✅ Derecho de rectificación
- ✅ Derecho de cancelación
- ✅ Derecho de oposición (ARCO)

#### OWASP Top 10 (2021)

| Riesgo | Estado | Controles Implementados |
|--------|--------|-------------------------|
| A01:2021 – Broken Access Control | ✅ | RBAC, validación tokens, permisos |
| A02:2021 – Cryptographic Failures | ✅ | HTTPS, Argon2, TLS 1.3 |
| A03:2021 – Injection | ✅ | ORM, sanitización, validación |
| A04:2021 – Insecure Design | ✅ | Security by design, threat modeling |
| A05:2021 – Security Misconfiguration | ✅ | Defaults seguros, headers |
| A06:2021 – Vulnerable Components | ✅ | Actualización continua, pip-audit |
| A07:2021 – Auth Failures | ✅ | JWT, Argon2, rate limiting |
| A08:2021 – Software & Data Integrity | ✅ | Validación, auditoría, logs |
| A09:2021 – Logging Failures | ✅ | Audit logs, monitoreo |
| A10:2021 – SSRF | ✅ | Validación URLs, whitelist |

### 5.6 Plan de Respuesta a Incidentes

#### Procedimiento

1. **Detección**
   - Monitoreo de logs
   - Alertas automáticas
   - Reportes de usuarios

2. **Contención**
   - Aislar sistema afectado
   - Bloquear IPs maliciosas
   - Revocar tokens comprometidos

3. **Erradicación**
   - Identificar vulnerabilidad
   - Aplicar parche
   - Verificar otros sistemas

4. **Recuperación**
   - Restaurar desde backup
   - Verificar integridad
   - Monitoreo intensivo

5. **Post-Incidente**
   - Análisis de causa raíz
   - Documentación
   - Actualizar procedimientos

### 5.7 Checklist de Seguridad para Producción

Antes de desplegar en producción, verificar:

#### Infraestructura
- [ ] HTTPS configurado (TLS 1.3)
- [ ] Certificados SSL válidos
- [ ] Firewall configurado (solo 80, 443)
- [ ] Backups automáticos diarios
- [ ] Monitoreo activo (Grafana, Prometheus)

#### Aplicación
- [ ] DEBUG=false en .env
- [ ] SECRET_KEY único y seguro (64+ caracteres)
- [ ] Contraseñas de BD fuertes
- [ ] CORS configurado específicamente (no *)
- [ ] Rate limiting habilitado
- [ ] Logs de auditoría activos

#### Base de Datos
- [ ] PostgreSQL con contraseña fuerte
- [ ] Conexiones solo desde localhost/VPC
- [ ] Backups cifrados
- [ ] SSL/TLS para conexiones
- [ ] Usuario con permisos mínimos

#### Código
- [ ] Sin credenciales hardcodeadas
- [ ] Sin TODO/FIXME de seguridad
- [ ] Dependencias actualizadas
- [ ] Pruebas de seguridad pasadas
- [ ] Code review completado

---

## 6. Manual de Usuario

### 6.1 Guía Rápida para Contribuyentes

#### Paso 1: Registro

1. Acceder a la URL del sistema: `https://ica.alcaldia.gov.co`
2. Clic en "Registrarse"
3. Completar formulario:
   - Email (será su usuario)
   - Contraseña (mínimo 8 caracteres, mayúsculas, números)
   - Nombre completo
   - NIT o documento de identidad
4. Clic en "Registrarse"
5. Iniciar sesión con credenciales

#### Paso 2: Crear Nueva Declaración

1. En el dashboard, clic en "Nueva Declaración"
2. Diligenciar **Sección A - Información del Contribuyente**:
   - NIT o documento
   - Razón social o nombre
   - Dirección
   - Teléfono, email
   - Municipio
3. Diligenciar **Sección B - Base Gravable**:
   - Renglón 8: Ingresos del año
   - Renglón 9: Otros ingresos
   - Renglones 11-15: Devoluciones y descuentos
   - El sistema calcula automáticamente totales
4. Diligenciar **Sección C - Actividades Gravadas**:
   - Agregar cada actividad económica
   - Código CIIU
   - Descripción
   - Ingresos por actividad
   - Tarifa (por mil)
5. Revisar **Sección D - Liquidación del Impuesto** (calculada automáticamente)
6. Diligenciar **Sección E - Descuentos y Anticipos** (si aplica)
7. Revisar **Sección F - Total a Pagar**
8. Clic en "Guardar Borrador"

#### Paso 3: Firma Digital

1. Acceder a la declaración guardada
2. Verificar todos los datos
3. Leer declaración de responsabilidad
4. Firmar en el recuadro con mouse/dedo
5. Clic en "Confirmar Firma"

#### Paso 4: Generar y Descargar PDF

1. Clic en "Generar PDF Oficial"
2. Esperar generación (puede tomar 10-30 segundos)
3. Clic en "Descargar PDF"
4. El PDF incluye:
   - Logo de la alcaldía
   - Todos los datos del formulario
   - Firma digital
   - Número de radicado único
   - Código QR de verificación

### 6.2 Guía para Administradores de Alcaldía

#### Configurar Marca Blanca

1. Iniciar sesión con usuario administrador
2. Acceder a "Administración" → "Marca Blanca"
3. Configurar:
   - Nombre completo de la alcaldía
   - Logo institucional (PNG/JPG, máx 5MB)
   - Colores corporativos (hex)
   - Información de contacto
   - Pie de página
4. Configurar tarifas ICA:
   - Por código CIIU
   - Tarifa en por mil (ej: 10 = 1%)
5. Guardar cambios
6. Los cambios aplican inmediatamente para nuevas declaraciones

---

## 7. API Reference

### 7.1 Autenticación

#### POST /api/v1/auth/register

Registrar nuevo usuario.

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "Juan Pérez",
  "nit": "1234567890"
}
```

**Response 201**:
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "Juan Pérez",
  "role": "declarante",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

#### POST /api/v1/auth/login

Iniciar sesión.

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response 200**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### 7.2 Declaraciones

#### POST /api/v1/declarations/

Crear nueva declaración.

**Headers**:
```
Authorization: Bearer {access_token}
```

**Request Body**:
```json
{
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
}
```

**Response 201**:
```json
{
  "id": 1,
  "number": "ICA-2024-0001",
  "status": "BORRADOR",
  "calculated_values": {
    "row_10": 10500000,
    "row_16": 10300000,
    "total_impuesto": 80000
  },
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

#### POST /api/v1/declarations/{id}/sign

Firmar declaración.

**Headers**:
```
Authorization: Bearer {access_token}
```

**Request Body**:
```json
{
  "signature": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
}
```

**Response 200**:
```json
{
  "id": 1,
  "status": "FIRMADA",
  "signed_at": "2024-01-15T11:00:00Z"
}
```

---

#### POST /api/v1/declarations/{id}/generate-pdf

Generar PDF oficial.

**Response 200**:
```json
{
  "pdf_url": "/api/v1/declarations/1/download-pdf",
  "radicado": "ICA-2024-0001-ABC123",
  "generated_at": "2024-01-15T11:05:00Z"
}
```

---

### 7.3 Códigos de Error

| Código | Significado | Descripción |
|--------|-------------|-------------|
| 400 | Bad Request | Datos inválidos o faltantes |
| 401 | Unauthorized | No autenticado o token inválido |
| 403 | Forbidden | Sin permisos suficientes |
| 404 | Not Found | Recurso no encontrado |
| 422 | Unprocessable Entity | Error de validación |
| 429 | Too Many Requests | Rate limit excedido |
| 500 | Internal Server Error | Error del servidor |

---

## Anexos

### A. Glosario

- **ICA**: Impuesto de Industria y Comercio
- **CIIU**: Clasificación Industrial Internacional Uniforme
- **NIT**: Número de Identificación Tributaria
- **JWT**: JSON Web Token
- **RBAC**: Role-Based Access Control
- **XSS**: Cross-Site Scripting
- **CSRF**: Cross-Site Request Forgery
- **SQL Injection**: Inyección SQL
- **TLS**: Transport Layer Security
- **ORM**: Object-Relational Mapping

### B. Referencias

1. Formulario Único Nacional ICA - `Documents/formulario-ICA.md`
2. Ley 14 de 1983 - Impuesto de Industria y Comercio
3. Ley 1581 de 2012 - Protección de Datos Personales
4. OWASP Top 10 - 2021
5. CWE Top 25 - Common Weakness Enumeration
6. NIST Cybersecurity Framework

### C. Contacto y Soporte

Para soporte técnico o consultas:
- Email: soporte@proveedor.com
- Documentación: https://docs.sistema-ica.com
- Issues: GitHub repository

---

**Documento actualizado**: 19 de diciembre de 2024  
**Versión**: 1.0.0  
**Sistema**: ICA - Formulario Único Nacional
