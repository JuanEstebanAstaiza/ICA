# 🧪 Guía Rápida de Prueba - Sistema ICA

Esta guía te ayudará a verificar rápidamente que el sistema está funcionando correctamente con los datos de prueba.

## ✅ Pre-requisitos

Asegúrate de que el sistema esté corriendo:

```bash
# Iniciar con Docker
docker compose up -d

# Verificar que los servicios están activos
docker compose ps

# Deberías ver:
# - postgres (running)
# - redis (running)
# - backend (running)
# - frontend (running)
```

## 🔄 Paso 1: Crear Usuarios de Prueba

```bash
# Ejecutar el script de seed
docker compose exec backend python scripts/seed_data.py

# Deberías ver:
# ✅ Usuario creado: contribuyente@example.com (declarante)
# ✅ Usuario creado: empresa@demo.com (declarante)
# ✅ Usuario creado: admin@alcaldia.gov.co (admin_alcaldia)
# ✅ Usuario creado: superadmin@sistema.com (admin_sistema)
```

## 🌐 Paso 2: Acceder a la Plataforma

1. **Abrir navegador** en: `http://localhost:3000/static/templates/login.html`

2. **Probar Login** con:
   - Email: `contribuyente@example.com`
   - Contraseña: `Test1234!`

3. **Deberías ver** el dashboard del usuario

## 📝 Paso 3: Probar Registro

1. **Ir a** `http://localhost:3000/static/templates/register.html`

2. **Completar formulario** con:
   - Email: `nuevo@test.com`
   - Nombre: Tu Nombre
   - Contraseña: `MiPassword123!`
   - Confirmar contraseña: `MiPassword123!`

3. **Hacer clic** en "Crear Cuenta"

4. **Deberías ser redirigido** al login automáticamente

5. **Iniciar sesión** con las nuevas credenciales

## 📊 Paso 4: Crear Declaración de Prueba

1. **En el dashboard**, hacer clic en "Nueva Declaración"

2. **Usar datos del Ejemplo 1** de `docs/DATOS_PRUEBA.md`:
   ```
   NIT: 900123456-7
   Razón Social: Tienda El Buen Precio SAS
   Ingresos brutos: $50,000,000
   ```

3. **Verificar** que los cálculos automáticos funcionan

4. **Guardar** como borrador

## 🔍 Verificaciones Adicionales

### API Documentation
- **Abrir**: `http://localhost:8000/api/docs`
- **Verificar** que todos los endpoints están documentados
- **Probar** el endpoint de registro directamente desde Swagger

### Health Check
```bash
curl http://localhost:8000/health
# Debería retornar: {"status":"healthy","version":"1.0.0"}
```

### Base de Datos
```bash
# Conectar a PostgreSQL
docker compose exec postgres psql -U ica_user -d ica_db

# Ver usuarios creados
SELECT email, full_name, role FROM users;

# Salir
\q
```

## ❌ Troubleshooting

### Problema: No puedo acceder al frontend
```bash
# Verificar que el servicio esté corriendo
docker compose logs frontend

# Verificar puerto
docker compose ps | grep frontend
```

### Problema: Error al crear usuarios
```bash
# Verificar logs del backend
docker compose logs backend

# Reiniciar servicios
docker compose restart backend
```

### Problema: Las contraseñas no funcionan
```bash
# Recrear usuarios de prueba
docker compose exec backend python scripts/seed_data.py
```

## 📚 Documentación Completa

Para más información detallada, consulta:

- **Datos de Prueba**: `docs/DATOS_PRUEBA.md`
- **Guía de Pruebas**: `docs/TESTING.md`
- **Documentación Docker**: `docs/DOCKER.md`
- **README Principal**: `README.md`

## ✅ Checklist de Verificación

- [ ] Servicios Docker están corriendo
- [ ] Script de seed ejecutado exitosamente
- [ ] Login funciona con credenciales de prueba
- [ ] Registro de nuevo usuario funciona
- [ ] Dashboard se carga correctamente
- [ ] Documentación API accesible
- [ ] Health check responde correctamente

---

**¡Sistema listo para usar! 🎉**
