# Sistema ICA - Formulario Único Nacional de Declaración y Pago

Sistema web institucional para el diligenciamiento del Formulario Único Nacional de Declaración y Pago del Impuesto de Industria y Comercio (ICA).

## 📋 Descripción

Plataforma web marca blanca y multi-alcaldía que permite:

- ✅ Autenticación de usuarios internos
- ✅ Creación y diligenciamiento del formulario ICA
- ✅ Cálculo automático conforme a normativa
- ✅ Firma digital del formulario
- ✅ Generación de PDF institucional
- ✅ Almacenamiento local del PDF en el servidor
- ✅ Descarga del PDF por el usuario
- ✅ Personalización completa por cada alcaldía (marca blanca)

## 🏗️ Arquitectura

```
ICA/
├── Documents/                    # Documentación fuente
│   └── formulario-ICA.md        # Single source of truth
├── backend/                      # API FastAPI
│   ├── app/
│   │   ├── api/                 # Endpoints REST
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py      # Autenticación JWT
│   │   │   │   ├── declarations.py  # CRUD declaraciones ICA
│   │   │   │   └── admin.py     # Administración y marca blanca
│   │   │   └── middleware/
│   │   │       └── security.py  # Headers, rate limiting, sanitización
│   │   ├── core/
│   │   │   ├── config.py        # Configuración (env vars)
│   │   │   └── security.py      # JWT, Argon2, CSRF
│   │   ├── db/
│   │   │   └── database.py      # PostgreSQL + SQLAlchemy
│   │   ├── models/
│   │   │   └── models.py        # Modelos de datos
│   │   ├── schemas/
│   │   │   └── schemas.py       # Validación Pydantic
│   │   ├── services/
│   │   │   ├── calculation_engine.py  # Motor de reglas
│   │   │   └── pdf_generator.py      # Generación PDF
│   │   └── utils/
│   │       └── validators.py    # Validaciones adicionales
│   ├── tests/
│   └── requirements.txt
├── frontend/                     # HTML/CSS/JS puro
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── api.js              # Cliente API
│   │   ├── ica-form.js         # Lógica del formulario
│   │   └── signature.js        # Firma digital canvas
│   └── templates/
│       ├── login.html
│       ├── dashboard.html
│       ├── form.html           # Formulario ICA completo
│       └── admin.html          # Panel marca blanca
├── docs/                        # Documentación de despliegue
└── migrations/                  # Migraciones de base de datos
```

## 🔐 Seguridad

El sistema implementa **security by design**:

- **Autenticación JWT** con tokens de acceso y refresco
- **Hash de contraseñas con Argon2** (algoritmo recomendado)
- **Protección CSRF** con tokens
- **Headers de seguridad** (XSS, Clickjacking, etc.)
- **Rate limiting** por IP
- **Sanitización de inputs** contra XSS y SQL Injection
- **Logs de auditoría** para todas las operaciones
- **Cifrado de datos sensibles** en reposo (configurable)

## 📊 Secciones del Formulario ICA

Basado en `Documents/formulario-ICA.md`:

| Sección | Descripción | Renglones |
|---------|-------------|-----------|
| **A** | Información del Contribuyente | Identificación + Ubicación |
| **B** | Base Gravable | 8-16 |
| **C** | Actividades Gravadas | CIIU + Tarifas |
| **D** | Liquidación del Impuesto | 30-33 |
| **E** | Descuentos, Créditos y Anticipos | - |
| **F** | Total a Pagar / Saldo a Favor | - |
| **G** | Firma y Responsabilidad | Firma digital |

### Fórmulas Implementadas

```python
# Renglón 10: Total ingresos
row_10 = row_8 + row_9

# Renglón 16: Total ingresos gravables
row_16 = row_10 - (row_11 + row_12 + row_13 + row_14 + row_15)

# Impuesto por actividad (tarifa en por mil)
tax = income * rate / 1000

# Renglón 33: Total impuesto
row_33 = row_30 + row_31 + row_32

# Saldo a pagar
balance = row_33 - (discounts + advances + withholdings)
```

## 👥 Roles de Usuario

1. **Declarante**: Usuario que diligencia formularios
2. **Administrador de Alcaldía**: Gestiona configuración del municipio
3. **Administrador del Sistema**: Control total del sistema

## 🚀 Instalación y Despliegue

### Requisitos

- Python 3.10+
- PostgreSQL 14+
- Redis (opcional, para cache)

### Instalación Local

```bash
# 1. Clonar repositorio
cd /opt
git clone <repository_url> ica-system

# 2. Crear entorno virtual
cd ica-system/backend
python -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con los valores correctos

# 5. Crear base de datos
createdb ica_db

# 6. Ejecutar migraciones
alembic upgrade head

# 7. Iniciar servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Variables de Entorno

```env
# Aplicación
APP_NAME="Formulario Único Nacional ICA"
DEBUG=false

# Base de datos
DATABASE_URL=postgresql://user:password@localhost:5432/ica_db

# Seguridad
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Almacenamiento
PDF_STORAGE_PATH=/var/ica/pdfs
ASSETS_STORAGE_PATH=/var/ica/assets
```

## 📖 API Documentation

La documentación OpenAPI está disponible en:

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

### Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Iniciar sesión |
| POST | `/api/v1/auth/register` | Registrar usuario |
| GET | `/api/v1/declarations/` | Listar declaraciones |
| POST | `/api/v1/declarations/` | Crear declaración |
| PUT | `/api/v1/declarations/{id}` | Actualizar declaración |
| POST | `/api/v1/declarations/{id}/sign` | Firmar declaración |
| POST | `/api/v1/declarations/{id}/generate-pdf` | Generar PDF |
| GET | `/api/v1/declarations/{id}/download-pdf` | Descargar PDF |
| PUT | `/api/v1/admin/white-label/{id}` | Configurar marca blanca |

## 📄 Licencia

Software propietario. El proveedor entrega software seguro por diseño, documentación y lineamientos, pero no administra la infraestructura.

---

**Basado en:** `Documents/formulario-ICA.md` - Formulario Único Nacional de Declaración y Pago ICA
