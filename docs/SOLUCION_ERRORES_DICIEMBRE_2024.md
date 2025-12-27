# Solución de Errores - Diciembre 2024

## Problemas Reportados

1. **Error interno del servidor (Internal Server Error)**
2. **El municipio no se muestra para el administrador de alcaldía**
3. **No se puede eliminar un administrador desde el panel de super administrador**

---

## Soluciones Implementadas

### 1. Municipio no visible para administradores

**Problema**: Al iniciar sesión como administrador de alcaldía, el municipio asociado no se mostraba en la interfaz.

**Causa**: El endpoint `/api/v1/auth/me` no cargaba la relación del municipio de forma explícita (eager loading), lo que causaba que la información del municipio no estuviera disponible en la respuesta.

**Solución**: Se modificó la función `get_current_user` en `backend/app/api/endpoints/auth.py` para usar `joinedload` de SQLAlchemy:

```python
from sqlalchemy.orm import joinedload

# Eagerly load the municipality relationship
user = db.query(User).options(
    joinedload(User.municipality)
).filter(User.id == int(user_id)).first()
```

### 2. Lista de usuarios sin información del municipio

**Problema**: En el panel de super administrador, la tabla de usuarios no mostraba el municipio asociado a cada usuario.

**Causa**: El endpoint `/api/v1/admin/users` no incluía la información del municipio en la respuesta.

**Solución**: Se modificó la función `list_users` en `backend/app/api/endpoints/admin.py`:

1. Se agregó `joinedload` para cargar la relación del municipio
2. Se incluyeron los campos `municipality_name` y `municipality_department` en la respuesta:

```python
return [
    {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role.value,
        "is_active": u.is_active,
        "municipality_id": u.municipality_id,
        "municipality_name": u.municipality.name if u.municipality else None,
        "municipality_department": u.municipality.department if u.municipality else None
    }
    for u in users
]
```

### 3. Error al eliminar administrador

**Problema**: Al intentar eliminar un administrador de alcaldía desde el panel de super admin, se producía un error interno del servidor.

**Causa**: Existían restricciones de llaves foráneas (foreign key constraints) que impedían la eliminación:
- Las declaraciones ICA tienen una referencia al usuario (`user_id`)
- Los logs de auditoría referencian al usuario
- La configuración de marca blanca tiene un campo `updated_by`
- Los parámetros de fórmulas tienen un campo `updated_by`

**Solución**: Se modificó la función `delete_user` en `backend/app/api/endpoints/admin.py`:

1. **Verificación de declaraciones**: Antes de eliminar, se verifica si el usuario tiene declaraciones asociadas:
```python
declarations_count = db.query(ICADeclaration).filter(
    ICADeclaration.user_id == user_id
).count()

if declarations_count > 0:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"No se puede eliminar el usuario porque tiene {declarations_count} declaración(es) asociada(s)."
    )
```

2. **Limpieza de referencias**: Se limpian las referencias en otras tablas antes de eliminar:
```python
# Limpiar referencias en audit_logs
db.query(AuditLog).filter(AuditLog.user_id == user_id).update(
    {AuditLog.user_id: None},
    synchronize_session='fetch'
)

# Limpiar referencias en white_label_configs
db.query(WhiteLabelConfig).filter(WhiteLabelConfig.updated_by == user_id).update(
    {WhiteLabelConfig.updated_by: None},
    synchronize_session='fetch'
)

# Limpiar referencias en formula_parameters
db.query(FormulaParameters).filter(FormulaParameters.updated_by == user_id).update(
    {FormulaParameters.updated_by: None},
    synchronize_session='fetch'
)
```

3. **Manejo de errores**: Se agregó manejo de excepciones para capturar cualquier error:
```python
try:
    # ... operaciones de eliminación ...
except Exception as e:
    db.rollback()
    logger.error(f"Error al eliminar usuario: {type(e).__name__}: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al eliminar el usuario: {str(e)}"
    )
```

---

## Cambios en Frontend

### superadmin.html

Se actualizó para usar la información del municipio directamente de la respuesta de la API:

```javascript
// Antes
const municipality = allMunicipalities.find(m => m.id === user.municipality_id);
const municipalityName = municipality ? `${municipality.name}` : '-';

// Después
let municipalityName = '-';
if (user.municipality_name) {
    municipalityName = `${user.municipality_name} (${user.municipality_department || ''})`;
} else if (user.municipality_id) {
    const municipality = allMunicipalities.find(m => m.id === user.municipality_id);
    municipalityName = municipality ? `${municipality.name}` : '-';
}
```

### admin.html

Se actualizó la función `setupFixedMunicipality` para usar la información del municipio del objeto usuario:

```javascript
// Buscar el municipio - primero desde user.municipality (de la API)
// Si no, buscar en allMunicipalities
let municipality = user.municipality;
if (!municipality && user.municipality_id) {
    municipality = allMunicipalities.find(m => m.id === user.municipality_id);
}
```

---

## Flujo Correcto para Cambiar Municipio de Plataforma

Si necesita cambiar el municipio asociado a la plataforma, siga estos pasos:

1. **Si el administrador tiene declaraciones**:
   - Use la opción "Limpiar Datos del Municipio" para eliminar las declaraciones primero
   - Luego elimine el administrador

2. **Si el administrador no tiene declaraciones**:
   - Simplemente elimine el administrador usando el selector "Eliminar Admin de Alcaldía"

3. **Crear nuevo administrador**:
   - Use el botón "Crear Usuario Admin"
   - Asigne el nuevo municipio al administrador

---

## Archivos Modificados

- `backend/app/api/endpoints/auth.py` - Carga eager de municipio en autenticación
- `backend/app/api/endpoints/admin.py` - Lista usuarios con municipio, eliminación mejorada
- `frontend/templates/superadmin.html` - Uso de datos de municipio de API
- `frontend/templates/admin.html` - Uso de datos de municipio del objeto usuario

---

## Verificación

Para verificar que los cambios funcionan correctamente:

1. Inicie sesión como super administrador
2. Verifique que los usuarios muestran su municipio asociado
3. Intente eliminar un administrador que no tenga declaraciones
4. Inicie sesión como administrador de alcaldía
5. Verifique que se muestra el municipio asignado en el panel de configuración

---

*Documento generado el 27 de diciembre de 2024*
