# Formulario Único Nacional de Declaración y Pago ICA

> **Origen**: Archivo Excel `FORMULARIO-UNICO-ICA-NACIONAL PARA TRABAJO DE APLICATIVO.xls`
>
> **Objetivo**: Este documento describe **todos los campos, secciones, renglones y reglas** del formulario ICA con el fin de permitir la **automatización parcial de la generación del documento** y su posterior renderización (PDF/Excel/Web).

---

## 1. Metadatos Generales del Formulario

* **Nombre oficial**: Formulario Único Nacional de Declaración y Pago del Impuesto de Industria y Comercio (ICA)
* **Tipo**: Declaración tributaria
* **Periodicidad**: Anual
* **Año gravable**: Campo editable
* **Municipio o Distrito**: Campo obligatorio
* **Departamento**: Campo obligatorio

> ⚠️ Nota técnica: En el Excel original, estos campos ocupan filas completas usadas solo para presentación visual.

---

## 2. Opción de Uso del Formulario

Campo de selección única:

* Declaración inicial
* Corrección
* Corrección que disminuye valor a pagar
* Corrección que aumenta valor a pagar

```json
{
  "tipo_declaracion": "inicial | correccion | correccion_disminuye | correccion_aumenta"
}
```

---

## 3. Sección A – Información del Contribuyente

### 3.1 Identificación

* Tipo de documento
* Número de documento / NIT
* Dígito de verificación
* Razón social / Nombre completo

### 3.2 Ubicación

* Dirección
* Municipio
* Departamento
* Teléfono
* Correo electrónico

> 🧠 Automatización sugerida: Autocompletar municipio y departamento desde un catálogo DANE.

---

## 4. Sección B – Base Gravable

Cada renglón del formulario corresponde a un **concepto tributario**.

### Renglones Base

| Renglón | Concepto                  | Tipo      |
| ------- | ------------------------- | --------- |
| 8       | Total ingresos ordinarios | Numérico  |
| 9       | Ingresos extraordinarios  | Numérico  |
| 10      | Total ingresos            | Calculado |
| 11      | Devoluciones              | Numérico  |
| 12      | Exportaciones             | Numérico  |
| 13      | Ventas de activos fijos   | Numérico  |
| 14      | Ingresos excluidos        | Numérico  |
| 15      | Ingresos no gravados      | Numérico  |

### Fórmula Clave

**TOTAL INGRESOS GRAVABLES**

> Renglón 16 = Renglón 10 – (11 + 12 + 13 + 14 + 15)

```python
total_ingresos_gravables = total_ingresos - (
    devoluciones + exportaciones + ventas_activos + excluidos + no_gravados
)
```

⚠️ Este texto aparece literalmente en el Excel como:

> *"TOTAL INGRESOS GRAVABLES (RENGLÓN 10 MENOS 11,12,13,14 Y 15)"*

---

## 5. Sección C – Actividades Gravadas

Por cada actividad:

* Código de actividad (CIIU)
* Descripción
* Ingresos asociados
* Tarifa ICA
* Impuesto generado

```json
{
  "actividad": {
    "ciiu": "string",
    "descripcion": "string",
    "ingresos": "number",
    "tarifa": "number",
    "impuesto": "number"
  }
}
```

---

## 6. Sección D – Liquidación del Impuesto

| Renglón | Concepto                         |
| ------- | -------------------------------- |
| 30      | Impuesto de Industria y Comercio |
| 31      | Avisos y Tableros                |
| 32      | Sobretasa                        |
| 33      | Total impuesto                   |

---

## 7. Sección E – Descuentos, Créditos y Anticipos

* Descuentos tributarios
* Anticipos pagados
* Retenciones sufridas

```python
saldo_a_pagar = total_impuesto - (anticipos + retenciones + descuentos)
```

---

## 8. Sección F – Total a Pagar / Saldo a Favor

* Total a pagar
* Saldo a favor del contribuyente

> Validación: **Nunca ambos al mismo tiempo**.

---

## 9. Sección G – Firma y Responsabilidad

Campos no automatizables (por normativa):

* Nombre del declarante
* Firma
* Fecha
* Nombre del contador / revisor fiscal
* Número de tarjeta profesional

> ⚠️ En el Excel estas filas existen únicamente para permitir firmas manuscritas.

---

## 10. Consideraciones Técnicas para la Aplicación

### 10.1 Campos que NO deben persistirse

* Filas vacías
* Filas de separación visual
* Filas destinadas solo a firma física

### 10.2 Campos Calculados

* Total ingresos
* Total ingresos gravables
* Total impuesto
* Saldo a pagar

> Estos campos **no deben ser editables**.

### 10.3 Modelo de Datos Base

```json
{
  "periodo": "YYYY",
  "municipio": "string",
  "contribuyente": {},
  "ingresos": {},
  "actividades": [],
  "liquidacion": {},
  "resultado": {}
}
```

---

## 11. Observación Final

El Excel original utiliza **filas nativas como recurso de maquetación**, lo cual **no debe replicarse en la base de datos**. La aplicación debe trabajar con **estructura lógica**, no visual.

---

📌 **Este documento está listo para ser usado como input directo para:**

* Generador de formularios web
* Motor de validaciones
* Generador de PDF
* Sistema de autollenado tributario

Si necesitas, puedo:

* Convertir esto en **JSON Schema**
* Diseñar el **modelo SQL**
* Generar el **backend en FastAPI**
* Crear el **motor de reglas de cálculo**
