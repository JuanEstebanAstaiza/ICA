# Documentación de Commits Recientes - Sistema ICA

Este documento describe los últimos commits realizados en el sistema ICA y los cambios implementados.

---

## Commit beeb9b1

**Mensaje:** Fix signatures in correction PDFs and add Colombia timezone support  
**Autor:** copilot-swe-agent[bot]  
**Fecha:** 2025-12-26  

### Descripción
Este commit soluciona dos problemas críticos:
1. Las firmas digitales no aparecían en el PDF cuando la declaración era una corrección
2. La hora de Colombia no se estaba utilizando consistentemente en el sistema

### Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `backend/app/api/endpoints/auth.py` | Añadido endpoint `/api/v1/auth/colombia-time` para obtener la hora de Colombia |
| `backend/app/services/pdf_generator.py` | Corregida la sección de firmas para mostrar tanto firma del declarante como del contador/revisor fiscal |
| `frontend/js/api.js` | Añadida función `AuthAPI.getColombiaTime()` |
| `frontend/templates/dashboard.html` | Agregado indicador de hora Colombia en el panel de control |
| `frontend/templates/form.html` | Agregado indicador de hora Colombia en modal de firma, fecha de declaración usa hora Colombia |

### Cambios Detallados

#### 1. Corrección de Firmas en PDF (`pdf_generator.py`)
- **Problema:** La firma del declarante se buscaba en `data.get('signature_data')` pero en correcciones se guarda en `signature_info.declarant_signature_image`
- **Solución:** Se modificó `_build_signature_section()` para:
  - Buscar la firma en `signature_info.declarant_signature_image` primero, luego en `data.signature_data`
  - Mostrar la firma del contador/revisor fiscal si existe (`accountant_signature_image`)
  - Mostrar información de integridad (fecha firmado y hash)

#### 2. Hora de Colombia (`auth.py`)
- **Nuevo endpoint:** `GET /api/v1/auth/colombia-time`
- **Retorna:** Fecha/hora en zona horaria UTC-5 (Colombia)
- **Formato de respuesta:**
```json
{
  "datetime": "2025-12-26T02:30:00-05:00",
  "date": "2025-12-26",
  "time": "02:30:00",
  "formatted": "26/12/2025 02:30:00",
  "timezone": "America/Bogota (UTC-5)"
}
```

#### 3. Frontend - Hora Colombia
- El dashboard muestra la hora actual de Colombia
- El modal de firma muestra la hora Colombia y la fecha se inicializa con fecha de Colombia
- El footer del PDF muestra "Documento generado el [fecha] (Hora Colombia)"

---

## Commit 97ec83a

**Mensaje:** Initial plan  
**Autor:** copilot-swe-agent[bot]  
**Fecha:** 2025-12-26  

### Descripción
Commit inicial de planificación para el análisis del problema.

---

## Commit f9e70b3

**Mensaje:** Enhance declaration correction and search functionalities  
**Autor:** Juan Esteban Astaiza Fuenmayor  
**Fecha:** 2025-12-25  

### Descripción
Mejoras en la funcionalidad de corrección de declaraciones y búsqueda.

### Funcionalidades Implementadas
- Sistema de corrección de declaraciones firmadas
- Endpoint de búsqueda de declaraciones por múltiples criterios
- Mejoras en la gestión de formularios para administradores

---

# Resumen de Mejoras

## Problemas Solucionados

### 1. Firmas en PDFs de Correcciones
**Antes:** Cuando un usuario firmaba una declaración de corrección, las firmas no aparecían en el PDF generado.
**Después:** Las firmas del declarante y del contador/revisor fiscal (si aplica) se muestran correctamente en todos los PDFs.

### 2. Hora de Colombia
**Antes:** El sistema usaba la hora del servidor (UTC) que no correspondía a la hora oficial de Colombia.
**Después:** 
- El PDF muestra "Documento generado el [fecha] (Hora Colombia)"
- El dashboard muestra un reloj con la hora de Colombia
- El modal de firma muestra la hora de Colombia para que el usuario sepa la hora exacta de radicación
- La fecha de declaración se inicializa con la fecha de Colombia (UTC-5)

### 3. Motor de Búsqueda para Administradores
**Estado:** Verificado que el endpoint `/api/v1/declarations/search` existe y funciona correctamente.
- Soporta búsqueda por número de radicado (`filing_number`)
- Soporta búsqueda por número de formulario (`form_number`)
- Soporta búsqueda por documento del contribuyente (`document_number`)
- Filtra resultados según rol del usuario (declarante ve solo sus declaraciones, admin de alcaldía ve las de su municipio, admin sistema ve todas)

---

# Notas Técnicas

## Endpoint de Hora Colombia
```python
@router.get("/colombia-time")
async def get_colombia_time_endpoint():
    """
    Obtiene la fecha y hora actual en zona horaria de Colombia (UTC-5).
    """
    colombia_now = get_colombia_time()
    return {
        "datetime": colombia_now.isoformat(),
        "date": colombia_now.strftime('%Y-%m-%d'),
        "time": colombia_now.strftime('%H:%M:%S'),
        "formatted": colombia_now.strftime('%d/%m/%Y %H:%M:%S'),
        "timezone": "America/Bogota (UTC-5)"
    }
```

## Función get_colombia_time() en config.py
```python
from datetime import timezone, timedelta

COLOMBIA_TZ = timezone(timedelta(hours=-5))

def get_colombia_time():
    """Obtiene la fecha/hora actual en zona horaria de Colombia."""
    from datetime import datetime
    return datetime.now(COLOMBIA_TZ)
```

## Sección de Firmas en PDF
La función `_build_signature_section()` ahora:
1. Obtiene datos de `signature_info`
2. Muestra datos del declarante (nombre, documento, fecha)
3. Muestra firma digital del declarante si existe
4. Muestra datos del contador/revisor fiscal si `requires_fiscal_reviewer` es True
5. Muestra firma digital del contador si existe
6. Muestra información de integridad (fecha firmado, hash)
