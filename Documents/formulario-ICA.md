# Formulario Único ICA – Versión Digital Tipo Medellín (SSOT)

> **Estado**: DEFINITIVO
>
> **Propósito**: Este documento es la **fuente única de verdad (Single Source of Truth)** para generar una aplicación web ICA cuyo formulario sea **funcional y visualmente equivalente** al formulario digital usado por municipios como Medellín, incorporando **firma digital avanzada**.

---

## 0. METADATOS DEL FORMULARIO (SISTEMA)

> Campos generados y controlados por el sistema, no editables por el usuario.

* **Periodo gravable** (YYYY)
* **Fecha de presentación** (ISO-8601)
* **Tipo de declaración**:

  * Inicial
  * Corrección
* **Consecutivo del formulario** (único)
* **Número de radicado** (único, posterior a firma)
* **Estado de la declaración**:

  * En borrador
  * Firmada
  * Presentada

---

## A. INFORMACIÓN DEL CONTRIBUYENTE

### 1. Apellidos y nombres / Razón social

### Tipo de entidad

* Privada
* Pública

### 2. Cédula o NIT

* Número
* Dígito de verificación (DV)

### 3. Dirección de notificación

* Dirección
* Departamento
* Municipio

### 4. Teléfono

### 5. Correo electrónico

### 6. Número de establecimientos en el municipio

### 7. Clasificación del contribuyente

* Común
* Simplificado

---

## B. BASE GRAVABLE

### 8. Total ingresos ordinarios y extraordinarios del período en todo el país

### 9. Menos ingresos fuera del municipio

### 10. Total ingresos ordinarios y extraordinarios en el municipio

* **Fórmula**: Renglón 8 − 9

### 11. Menos ingresos por devoluciones, rebajas y descuentos

### 12. Menos ingresos por exportaciones y venta de activos fijos

### 13. Menos ingresos por actividades excluidas o no sujetas y otros ingresos no gravados

### 14. Menos ingresos por actividades exentas en el municipio

### 15. Total ingresos gravables

* **Fórmula**: Renglón 10 − (11 + 12 + 13 + 14)

---

## C. DISCRIMINACIÓN DE INGRESOS GRAVADOS Y ACTIVIDADES

Tabla dinámica de actividades (mínimo 1):

* Actividad (principal / secundaria)
* Código CIIU
* Ingresos gravados
* Tarifa (por mil)
* Impuesto ICA
* Tarifa especial (si aplica)

### 16. Total ingresos gravados en el municipio

### 17. Total impuesto ICA

* **Fórmula**: Suma de impuesto por actividad

### 18. Generación de energía – Capacidad instalada (kW)

### 19. Impuesto Ley 56 de 1981

---

## D. LIQUIDACIÓN DEL IMPUESTO

### 20. Total impuesto de industria y comercio

* **Fórmula**: Renglón 17 + 19

### 21. Impuesto de avisos y tableros

### 22. Pago por unidades comerciales adicionales del sector financiero

### 23. Sobretasa bomberil

### 24. Sobretasa de seguridad

### 25. Total impuesto a cargo

* **Fórmula**: 20 + 21 + 22 + 23 + 24

### 26. Menos exenciones o exoneraciones sobre el impuesto

### 27. Menos retenciones practicadas en el municipio

### 28. Menos autorretenciones practicadas en el municipio

### 29. Menos anticipo liquidado en el año anterior

### 30. Anticipo del año siguiente

### 31. Sanciones (checklist)

* Extemporaneidad
* Corrección
* Inexactitud
* Otra (especificar)

### 32. Menos saldo a favor del período anterior

### 33. Total saldo a cargo

### 34. Total saldo a favor

---

## E. PAGO

### 35. Valor a pagar

### 36. Descuento por pronto pago

### 37. Intereses de mora

### 38. Total a pagar

* **Fórmula**: 35 − 36 + 37

### 39. Pago voluntario

* Valor
* Destino del aporte

### 40. Total a pagar con pago voluntario

* **Fórmula**: 38 + 39

---

## F. FIRMAS DIGITALES

> Una vez firmada la declaración, **queda bloqueada para edición**.

### Firma del declarante

* Nombre
* Documento
* Método de firma:

  * Firma manuscrita (canvas)
  * Firma con clave
* Checkbox de declaración bajo juramento

### Firma del contador / revisor fiscal

* Aplica revisor fiscal (Sí / No)
* Nombre
* Documento
* Tarjeta profesional
* Método de firma

### Metadatos de firma (NO visibles)

* Hash del documento
* Fecha y hora
* IP
* User-Agent
* Integridad verificada

---

## G. CONTROL INSTITUCIONAL

* Número de radicado
* Fecha y hora de presentación
* Código de barras
* Código QR

> Campos de uso exclusivo del sistema o de la alcaldía

---

## REGLAS GENERALES

* Los campos calculados **no son editables**
* El radicado solo se genera tras firmas válidas
* El PDF generado debe reflejar exactamente este formulario
* Este documento reemplaza cualquier versión previa
