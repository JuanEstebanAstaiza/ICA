# 🧪 Datos de Prueba - Sistema ICA

Este documento contiene las credenciales y datos de prueba necesarios para acceder y probar el Sistema ICA.

## 📋 Índice

- [Credenciales de Usuario](#credenciales-de-usuario)
- [Cómo Acceder a la Plataforma](#cómo-acceder-a-la-plataforma)
- [Datos de Ejemplo para Declaraciones](#datos-de-ejemplo-para-declaraciones)
- [Crear Usuarios de Prueba](#crear-usuarios-de-prueba)
- [Importar Datos de Prueba](#importar-datos-de-prueba)

---

## 🔐 Credenciales de Usuario

### 1. Usuario Declarante (Contribuyente)

**Cuenta 1:**
- **Email**: `contribuyente@example.com`
- **Contraseña**: `Test1234!`
- **Rol**: Declarante
- **NIT**: `900123456-7`
- **Nombre**: Juan Pérez Empresa SAS
- **Permisos**: Crear, editar y firmar declaraciones propias

**Cuenta 2:**
- **Email**: `empresa@demo.com`
- **Contraseña**: `Demo2024!`
- **Rol**: Declarante
- **NIT**: `890456789-2`
- **Nombre**: Comercial Demo LTDA
- **Permisos**: Crear, editar y firmar declaraciones propias

---

### 2. Administrador de Alcaldía

**Cuenta:**
- **Email**: `admin@alcaldia.gov.co`
- **Contraseña**: `Admin2024!`
- **Rol**: Administrador de Alcaldía
- **NIT**: `899999123-1`
- **Nombre**: María González Administradora
- **Permisos**: 
  - Ver todas las declaraciones del municipio
  - Configurar marca blanca (logo, colores)
  - Configurar tarifas ICA
  - Gestionar usuarios del municipio

---

### 3. Administrador del Sistema

**Cuenta:**
- **Email**: `superadmin@sistema.com`
- **Contraseña**: `Super2024!`
- **Rol**: Administrador del Sistema
- **NIT**: `800000000-0`
- **Nombre**: Carlos Rodríguez SuperAdmin
- **Permisos**: 
  - Control total del sistema
  - Gestionar todos los municipios
  - Ver estadísticas globales
  - Gestionar todos los usuarios

---

## 🌐 Cómo Acceder a la Plataforma

### Opción 1: Con Docker (Recomendado)

```bash
# 1. Iniciar el sistema
cd ICA
docker compose up -d

# 2. Verificar que los servicios estén corriendo
docker compose ps

# 3. Acceder a la aplicación
# Abrir navegador en: http://localhost:3000

# 4. Iniciar sesión con cualquiera de las credenciales anteriores
```

### Opción 2: Instalación Local

```bash
# 1. Iniciar el backend
cd backend
source venv/bin/activate  # En Windows: venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. Acceder a la aplicación
# Frontend: http://localhost:3000
# API: http://localhost:8000
# Docs: http://localhost:8000/api/docs
```

### Verificar Acceso

1. **Abrir** `http://localhost:3000` en el navegador
2. **Ingresar** email y contraseña de alguna cuenta de prueba
3. **Hacer clic** en "Iniciar Sesión"
4. **Verificar** que accedes al dashboard

---

## 📊 Datos de Ejemplo para Declaraciones

### Ejemplo 1: Comercio al Por Menor

Usa estos datos para crear una declaración de prueba:

#### Sección A - Información del Contribuyente
```
NIT: 900123456-7
Razón Social: Tienda El Buen Precio SAS
Dirección: Calle 50 #25-30
Teléfono: 3001234567
Email: tienda@ejemplo.com
Municipio: Bogotá D.C.
Departamento: Cundinamarca
```

#### Sección B - Base Gravable
```
Renglón 8 - Ingresos brutos del año: $50,000,000
Renglón 9 - Otros ingresos: $2,000,000
Renglón 11 - Ingresos de actividades exentas: $0
Renglón 12 - Devoluciones, rebajas y descuentos: $1,500,000
Renglón 13 - Exportaciones: $0
Renglón 14 - Ingresos de otros municipios: $5,000,000
Renglón 15 - Otros ingresos no gravados: $500,000

✅ Renglón 10 (Calculado): $52,000,000
✅ Renglón 16 (Base gravable): $45,000,000
```

#### Sección C - Actividades Gravadas
```
Actividad 1:
  CIIU: 4711 - Comercio al por menor en establecimientos no especializados
  Descripción: Venta de productos de consumo masivo
  Ingresos: $30,000,000
  Tarifa: 10 por mil (1%)
  
Actividad 2:
  CIIU: 4773 - Comercio al por menor de productos farmacéuticos
  Descripción: Venta de medicamentos
  Ingresos: $15,000,000
  Tarifa: 8 por mil (0.8%)
```

#### Sección D - Liquidación del Impuesto
```
Renglón 30 - Impuesto actividad 1: $300,000 (30M × 10/1000)
Renglón 31 - Impuesto actividad 2: $120,000 (15M × 8/1000)
Renglón 32 - Otras actividades: $0
✅ Renglón 33 - Total impuesto: $420,000
```

#### Sección E - Descuentos y Anticipos
```
Descuentos tributarios: $20,000
Retenciones practicadas: $50,000
Anticipos pagados: $100,000
Total descuentos: $170,000
```

#### Sección F - Total a Pagar
```
✅ Total impuesto (R33): $420,000
✅ Menos descuentos: -$170,000
✅ TOTAL A PAGAR: $250,000
```

---

### Ejemplo 2: Servicios Profesionales

#### Sección A - Información del Contribuyente
```
NIT: 890456789-2
Razón Social: Consultoría Empresarial LTDA
Dirección: Carrera 15 #85-40
Teléfono: 3109876543
Email: consultoria@demo.com
Municipio: Medellín
Departamento: Antioquia
```

#### Sección B - Base Gravable
```
Renglón 8 - Ingresos brutos del año: $120,000,000
Renglón 9 - Otros ingresos: $5,000,000
Renglón 11 - Ingresos de actividades exentas: $0
Renglón 12 - Devoluciones, rebajas y descuentos: $3,000,000
Renglón 13 - Exportaciones: $10,000,000
Renglón 14 - Ingresos de otros municipios: $15,000,000
Renglón 15 - Otros ingresos no gravados: $2,000,000

✅ Renglón 10 (Calculado): $125,000,000
✅ Renglón 16 (Base gravable): $95,000,000
```

#### Sección C - Actividades Gravadas
```
Actividad 1:
  CIIU: 7020 - Actividades de consultoría de gestión
  Descripción: Consultoría empresarial
  Ingresos: $95,000,000
  Tarifa: 11.04 por mil (1.104%)
```

#### Sección D - Liquidación del Impuesto
```
Renglón 30 - Impuesto actividad 1: $1,048,800 (95M × 11.04/1000)
✅ Renglón 33 - Total impuesto: $1,048,800
```

#### Sección F - Total a Pagar
```
✅ Total impuesto (R33): $1,048,800
✅ Menos descuentos: $0
✅ TOTAL A PAGAR: $1,048,800
```

---

### Ejemplo 3: Restaurante

#### Sección A - Información del Contribuyente
```
NIT: 800321654-9
Razón Social: Restaurante El Sabor Colombiano
Dirección: Calle 72 #10-34
Teléfono: 3157894561
Email: restaurante@demo.com
Municipio: Cali
Departamento: Valle del Cauca
```

#### Sección B - Base Gravable
```
Renglón 8 - Ingresos brutos del año: $80,000,000
Renglón 9 - Otros ingresos: $3,000,000
Renglón 12 - Devoluciones, rebajas y descuentos: $2,000,000

✅ Renglón 10 (Calculado): $83,000,000
✅ Renglón 16 (Base gravable): $81,000,000
```

#### Sección C - Actividades Gravadas
```
Actividad 1:
  CIIU: 5611 - Expendio a la mesa de comidas preparadas
  Descripción: Servicio de restaurante
  Ingresos: $81,000,000
  Tarifa: 11.04 por mil (1.104%)
```

#### Sección D - Liquidación del Impuesto
```
Renglón 30 - Impuesto: $894,240 (81M × 11.04/1000)
✅ Renglón 33 - Total impuesto: $894,240
```

---

## 👥 Crear Usuarios de Prueba

### Método 1: Desde la Interfaz Web

1. **Acceder** a `http://localhost:3000`
2. **Hacer clic** en "Registrarse"
3. **Completar** el formulario:
   - Email
   - Contraseña (mínimo 8 caracteres, incluir mayúsculas y números)
   - Nombre completo
   - NIT
4. **Hacer clic** en "Registrarse"
5. **Iniciar sesión** con las nuevas credenciales

---

### Método 2: Desde la API (Swagger)

1. **Acceder** a `http://localhost:8000/api/docs`
2. **Expandir** el endpoint `POST /api/v1/auth/register`
3. **Hacer clic** en "Try it out"
4. **Ingresar** los datos:

```json
{
  "email": "nuevo@test.com",
  "password": "MiPassword123!",
  "full_name": "Nuevo Usuario",
  "nit": "123456789"
}
```

5. **Hacer clic** en "Execute"
6. **Verificar** respuesta 201 Created

---

### Método 3: Con cURL

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@nuevo.com",
    "password": "Password123!",
    "full_name": "Test Usuario",
    "nit": "987654321"
  }'
```

---

## 🔄 Importar Datos de Prueba

### Script de Inicialización de Datos

Crea un script para poblar la base de datos con usuarios de prueba:

```python
# backend/scripts/seed_data.py
"""Script para crear usuarios de prueba en la base de datos."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import SessionLocal, engine
from app.models.models import User, Base
from app.core.security import get_password_hash

def seed_users():
    """Crear usuarios de prueba."""
    
    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Lista de usuarios de prueba
        test_users = [
            {
                "email": "contribuyente@example.com",
                "password": "Test1234!",
                "full_name": "Juan Pérez Empresa SAS",
                "nit": "900123456-7",
                "role": "declarante"
            },
            {
                "email": "empresa@demo.com",
                "password": "Demo2024!",
                "full_name": "Comercial Demo LTDA",
                "nit": "890456789-2",
                "role": "declarante"
            },
            {
                "email": "admin@alcaldia.gov.co",
                "password": "Admin2024!",
                "full_name": "María González Administradora",
                "nit": "899999123-1",
                "role": "admin_alcaldia"
            },
            {
                "email": "superadmin@sistema.com",
                "password": "Super2024!",
                "full_name": "Carlos Rodríguez SuperAdmin",
                "nit": "800000000-0",
                "role": "admin_sistema"
            }
        ]
        
        # Crear cada usuario
        for user_data in test_users:
            # Verificar si el usuario ya existe
            existing_user = db.query(User).filter(
                User.email == user_data["email"]
            ).first()
            
            if not existing_user:
                # Hash de contraseña
                hashed_password = get_password_hash(user_data["password"])
                
                # Crear usuario
                user = User(
                    email=user_data["email"],
                    hashed_password=hashed_password,
                    full_name=user_data["full_name"],
                    nit=user_data["nit"],
                    role=user_data["role"],
                    is_active=True
                )
                
                db.add(user)
                print(f"✅ Usuario creado: {user_data['email']}")
            else:
                print(f"⚠️  Usuario ya existe: {user_data['email']}")
        
        # Guardar cambios
        db.commit()
        print("\n🎉 Datos de prueba importados exitosamente!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Creando datos de prueba...\n")
    seed_users()
```

### Ejecutar el Script

```bash
# Con Docker
docker compose exec backend python scripts/seed_data.py

# Sin Docker (local)
cd backend
source venv/bin/activate
python scripts/seed_data.py
```

---

## 🧪 Probar el Sistema Completo

### Flujo de Prueba Completo

1. **Iniciar sesión** con `contribuyente@example.com` / `Test1234!`
2. **Crear declaración** usando datos del Ejemplo 1
3. **Guardar borrador**
4. **Editar** y completar todos los campos
5. **Firmar** declaración (dibujar firma en el canvas)
6. **Generar PDF**
7. **Descargar PDF** y verificar contenido

---

### Probar Diferentes Roles

#### Como Declarante
- ✅ Crear declaraciones
- ✅ Editar borradores
- ✅ Firmar declaraciones
- ✅ Ver historial propio
- ❌ Ver declaraciones de otros
- ❌ Configurar marca blanca

#### Como Admin Alcaldía
- ✅ Ver todas las declaraciones del municipio
- ✅ Configurar marca blanca
- ✅ Configurar tarifas
- ❌ Gestionar otros municipios

#### Como Admin Sistema
- ✅ Control total
- ✅ Gestionar todos los municipios
- ✅ Ver estadísticas globales

---

## 🔒 Seguridad de las Credenciales

### ⚠️ IMPORTANTE

Estas credenciales son **SOLO PARA PRUEBAS Y DESARROLLO**.

**Nunca uses estas credenciales en producción.**

### Para Producción

1. **Cambiar** todas las contraseñas
2. **Usar** contraseñas fuertes (mínimo 12 caracteres)
3. **Habilitar** autenticación de dos factores (2FA)
4. **Revisar** permisos de usuarios regularmente
5. **Auditar** logs de acceso

---

## 📞 Soporte

Si tienes problemas para acceder con las credenciales de prueba:

1. **Verificar** que los servicios estén corriendo:
   ```bash
   docker compose ps
   ```

2. **Revisar logs** del backend:
   ```bash
   docker compose logs backend
   ```

3. **Recrear usuarios** ejecutando el script de seed:
   ```bash
   docker compose exec backend python scripts/seed_data.py
   ```

4. **Verificar** documentación completa en `docs/DOCUMENTACION_COMPLETA.md`

---

## ✅ Checklist de Verificación

Antes de probar, asegúrate de:

- [ ] Docker compose está corriendo
- [ ] PostgreSQL está activo
- [ ] Backend responde en `http://localhost:8000/health`
- [ ] Frontend está accesible en `http://localhost:3000`
- [ ] Puedes acceder a la documentación en `http://localhost:8000/api/docs`

---

**Última actualización**: 19 de diciembre de 2024  
**Sistema**: ICA - Formulario Único Nacional  
**Versión**: 1.0.0
