"""
Esquemas Pydantic para validación de datos.
Basado en: Documents/formulario-ICA.md
Implementa validación doble (frontend y backend).
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum
import re


# ===================== FUNCIONES DE VALIDACIÓN REUTILIZABLES =====================

def validate_password_strength(password: str) -> str:
    """
    Valida que la contraseña cumpla con los requisitos de seguridad.
    - Mínimo una mayúscula
    - Mínimo una minúscula
    - Mínimo un número
    """
    if not re.search(r'[A-Z]', password):
        raise ValueError('La contraseña debe contener al menos una mayúscula')
    if not re.search(r'[a-z]', password):
        raise ValueError('La contraseña debe contener al menos una minúscula')
    if not re.search(r'\d', password):
        raise ValueError('La contraseña debe contener al menos un número')
    return password


# ===================== ENUMS =====================

class UserRoleEnum(str, Enum):
    DECLARANTE = "declarante"
    ADMIN_ALCALDIA = "admin_alcaldia"
    ADMIN_SISTEMA = "admin_sistema"


class PersonTypeEnum(str, Enum):
    NATURAL = "natural"
    JURIDICA = "juridica"


class DeclarationTypeEnum(str, Enum):
    """
    Sección 2 - Opción de Uso del Formulario.
    tipo_declaracion: inicial | correccion | correccion_disminuye | correccion_aumenta
    """
    INICIAL = "inicial"
    CORRECCION = "correccion"
    CORRECCION_DISMINUYE = "correccion_disminuye"
    CORRECCION_AUMENTA = "correccion_aumenta"


class FormStatusEnum(str, Enum):
    BORRADOR = "borrador"
    COMPLETADO = "completado"
    FIRMADO = "firmado"
    ANULADO = "anulado"


# ===================== AUTENTICACIÓN =====================

class UserBase(BaseModel):
    """Datos básicos de usuario."""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class UserCreate(UserBase):
    """Registro simple (legacy) - usado por admins."""
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def password_strength(cls, v):
        return validate_password_strength(v)


class UserRegisterNatural(BaseModel):
    """
    Registro para PERSONA NATURAL.
    Los datos personales se usan para autocompletar el formulario ICA.
    """
    # Datos de autenticación
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    
    # Datos personales
    full_name: str = Field(..., min_length=2, max_length=255)
    document_type: str = Field(..., min_length=1, max_length=20)  # CC, CE, Pasaporte
    document_number: str = Field(..., min_length=5, max_length=20)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)  # Se autocompleta con municipio
    
    # NIT opcional para persona natural con actividad económica
    nit: Optional[str] = Field(None, max_length=20)
    
    @validator('password')
    def password_strength(cls, v):
        return validate_password_strength(v)
    
    @validator('document_number')
    def validate_document(cls, v):
        if re.search(r'[;\'"\\]', v):
            raise ValueError('Caracteres no permitidos en número de documento')
        return v


class UserRegisterJuridica(BaseModel):
    """
    Registro para PERSONA JURÍDICA.
    Incluye datos de la empresa y del representante legal.
    El login se hace con los datos del representante legal.
    Los datos se usan para autocompletar el formulario ICA.
    """
    # ===== DATOS DE LA EMPRESA =====
    company_name: str = Field(..., min_length=2, max_length=255)  # Razón social
    nit: str = Field(..., min_length=9, max_length=15)  # NIT de la empresa
    nit_verification_digit: Optional[str] = Field(None, max_length=1)  # Dígito de verificación
    company_address: Optional[str] = Field(None, max_length=500)  # Dirección empresa
    company_phone: Optional[str] = Field(None, max_length=20)
    company_email: Optional[EmailStr] = None  # Email corporativo
    economic_activity: Optional[str] = Field(None, max_length=255)  # Actividad económica
    
    # ===== DATOS DEL REPRESENTANTE LEGAL (usado para login) =====
    full_name: str = Field(..., min_length=2, max_length=255)  # Nombre del rep. legal
    document_type: str = Field(..., min_length=1, max_length=20)  # CC, CE
    document_number: str = Field(..., min_length=5, max_length=20)
    email: EmailStr  # Email del rep. legal (usado para login)
    password: str = Field(..., min_length=8, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)  # Dirección personal
    
    @validator('password')
    def password_strength(cls, v):
        return validate_password_strength(v)
    
    @validator('document_number')
    def validate_document(cls, v):
        if re.search(r'[;\'"\\]', v):
            raise ValueError('Caracteres no permitidos en número de documento')
        return v
    
    @validator('nit')
    def validate_nit(cls, v):
        # NIT debe ser numérico
        if not v.replace('-', '').replace('.', '').isdigit():
            raise ValueError('NIT debe contener solo números')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class AdminUserCreate(UserBase):
    """Schema para crear usuarios administradores desde el panel de super admin."""
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRoleEnum = UserRoleEnum.ADMIN_ALCALDIA
    municipality_id: Optional[int] = None
    
    @validator('password')
    def password_strength(cls, v):
        return validate_password_strength(v)


class UserStatusUpdate(BaseModel):
    """Schema para actualizar estado de usuario."""
    is_active: bool


class MunicipalityInfo(BaseModel):
    """Información básica del municipio para respuestas."""
    id: int
    code: str
    name: str
    department: str
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Respuesta completa de usuario con soporte para persona natural y jurídica."""
    id: int
    email: EmailStr
    full_name: str
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    
    # Tipo de persona
    person_type: Optional[PersonTypeEnum] = PersonTypeEnum.NATURAL
    
    # Datos de persona jurídica (si aplica)
    company_name: Optional[str] = None
    nit: Optional[str] = None
    nit_verification_digit: Optional[str] = None
    company_address: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    economic_activity: Optional[str] = None
    
    # Rol y estado
    role: UserRoleEnum
    is_active: bool
    municipality_id: Optional[int]
    municipality: Optional[MunicipalityInfo] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: datetime
    type: str


# ===================== ALCALDÍA / MUNICIPIO =====================

class MunicipalityBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=2, max_length=255)
    department: str = Field(..., min_length=2, max_length=255)


class MunicipalityCreate(MunicipalityBase):
    pass


class MunicipalityResponse(MunicipalityBase):
    id: int
    is_active: bool
    
    class Config:
        from_attributes = True


# ===================== CONFIGURACIÓN MARCA BLANCA =====================

class WhiteLabelConfigBase(BaseModel):
    logo_path: Optional[str] = None
    primary_color: str = Field(default="#003366", pattern=r'^#[0-9A-Fa-f]{6}$')
    secondary_color: str = Field(default="#0066CC", pattern=r'^#[0-9A-Fa-f]{6}$')
    accent_color: str = Field(default="#FF9900", pattern=r'^#[0-9A-Fa-f]{6}$')
    font_family: str = Field(default="Arial, sans-serif", max_length=100)
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    legal_notes: Optional[str] = None
    form_title: str = Field(
        default="Formulario Único Nacional de Declaración y Pago ICA",
        max_length=500
    )
    
    # Nombre de la aplicación personalizado (ej: "Alcaldía de Medellín - Sistema ICA")
    app_name: Optional[str] = Field(default="Sistema ICA", max_length=255)
    
    # Marca de agua para PDF (prevención de fraudes)
    watermark_text: Optional[str] = Field(default="", max_length=255)
    
    # Configuración de Numeración (Consecutivo y Radicado)
    consecutivo_prefijo: Optional[str] = Field(default="", max_length=10)
    consecutivo_actual: int = Field(default=1, ge=1)
    consecutivo_digitos: int = Field(default=12, ge=6, le=20)
    radicado_prefijo: Optional[str] = Field(default="", max_length=10)
    radicado_actual: int = Field(default=1, ge=1)
    radicado_digitos: int = Field(default=16, ge=6, le=20)


class WhiteLabelConfigUpdate(WhiteLabelConfigBase):
    pass


class WhiteLabelConfigResponse(WhiteLabelConfigBase):
    id: int
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ===================== PARÁMETROS DE FÓRMULAS CONFIGURABLES =====================

class FormulaParametersBase(BaseModel):
    """
    Parámetros configurables de fórmulas por municipio.
    Permite edición en caliente de valores numéricos de las fórmulas
    en caso de cambios en legislación.
    Basado en: Documents/formulario-ICA.md - Secciones D y E
    """
    # Parámetros de Avisos y Tableros (Sección D - Renglón 21)
    avisos_tableros_porcentaje: float = Field(default=15.0, ge=0, le=100)
    
    # Parámetros de Sobretasa Bomberil (Sección D - Renglón 23)
    sobretasa_bomberil_porcentaje: float = Field(default=0.0, ge=0, le=100)
    
    # Parámetros de Sobretasa Seguridad (Sección D - Renglón 24)
    sobretasa_seguridad_porcentaje: float = Field(default=0.0, ge=0, le=100)
    
    # Parámetros Ley 56 de 1981 - Generación de energía (Sección D - Renglón 19)
    ley_56_tarifa_por_kw: float = Field(default=0.0, ge=0)
    
    # Parámetros de Anticipo (Sección D - Renglón 30)
    anticipo_ano_siguiente_porcentaje: float = Field(default=40.0, ge=0, le=100)
    
    # Parámetros de Descuento por Pronto Pago (Sección E - Renglón 36)
    descuento_pronto_pago_porcentaje: float = Field(default=10.0, ge=0, le=100)
    descuento_pronto_pago_dias: int = Field(default=30, ge=0)
    
    # Parámetros de Intereses de Mora (Sección E - Renglón 37)
    interes_mora_mensual: float = Field(default=1.0, ge=0, le=100)
    
    # Parámetros de Unidades Comerciales Adicionales Sector Financiero (Sección D - Renglón 22)
    unidades_adicionales_financiero_valor: float = Field(default=0.0, ge=0)


class FormulaParametersCreate(FormulaParametersBase):
    municipality_id: int


class FormulaParametersUpdate(FormulaParametersBase):
    pass


class FormulaParametersResponse(FormulaParametersBase):
    id: int
    municipality_id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ===================== CONTRIBUYENTE - SECCIÓN A =====================

class TaxpayerBase(BaseModel):
    """
    Sección A – Información del Contribuyente.
    Basado en: Documents/formulario-ICA.md - Sección A
    """
    # Renglón 1: Identificación
    legal_name: str = Field(..., min_length=2, max_length=255)
    
    # Tipo de entidad (según formulario-ICA.md)
    entity_type: str = Field(default="privada", pattern=r'^(privada|publica)$')
    
    # Renglón 2: Cédula o NIT
    document_type: str = Field(..., min_length=1, max_length=20)
    document_number: str = Field(..., min_length=1, max_length=50)
    verification_digit: Optional[str] = Field(None, max_length=1)
    
    # Renglón 3: Dirección de notificación
    address: Optional[str] = Field(None, max_length=500)
    notification_department: Optional[str] = Field(None, max_length=255)
    notification_municipality: Optional[str] = Field(None, max_length=255)
    
    # Renglón 4: Teléfono
    phone: Optional[str] = Field(None, max_length=50)
    
    # Renglón 5: Correo electrónico
    email: Optional[EmailStr] = None
    
    # Renglón 6: Número de establecimientos en el municipio
    num_establishments: int = Field(default=1, ge=0)
    
    # Renglón 7: Clasificación del contribuyente
    taxpayer_classification: str = Field(default="comun", pattern=r'^(comun|simplificado)$')
    
    # Campos legacy para compatibilidad
    municipality: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=255)
    
    @validator('document_number')
    def validate_document(cls, v):
        # Sanitización contra SQL Injection
        if re.search(r'[;\'"\\]', v):
            raise ValueError('Caracteres no permitidos en número de documento')
        return v


class TaxpayerCreate(TaxpayerBase):
    pass


class TaxpayerResponse(BaseModel):
    """
    Respuesta de contribuyente - campos opcionales para permitir
    declaraciones recién creadas con datos vacíos.
    """
    id: int
    declaration_id: int
    
    # Campos opcionales para la respuesta (pueden estar vacíos al crear)
    legal_name: Optional[str] = None
    entity_type: Optional[str] = "privada"
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    verification_digit: Optional[str] = None
    address: Optional[str] = None
    municipality: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    num_establishments: Optional[int] = 1
    classification: Optional[str] = None
    is_consortium: Optional[bool] = False
    autonomous_patrimony: Optional[bool] = False
    
    class Config:
        from_attributes = True


# ===================== BASE GRAVABLE - SECCIÓN B =====================

class IncomeBaseSchema(BaseModel):
    """
    Sección B – Base Gravable.
    Basado en: Documents/formulario-ICA.md - Sección B, Renglones 8-15
    """
    # Renglón 8: Total ingresos ordinarios y extraordinarios del período en todo el país
    row_8_total_income_country: float = Field(default=0, ge=0)
    
    # Renglón 9: Menos ingresos fuera del municipio
    row_9_income_outside_municipality: float = Field(default=0, ge=0)
    
    # Renglón 10: Total ingresos en el municipio (Calculado: R8 - R9)
    # CAMPO CALCULADO - No editable
    
    # Renglón 11: Menos ingresos por devoluciones, rebajas y descuentos
    row_11_returns_rebates_discounts: float = Field(default=0, ge=0)
    
    # Renglón 12: Menos ingresos por exportaciones y venta de activos fijos
    row_12_exports_fixed_assets: float = Field(default=0, ge=0)
    
    # Renglón 13: Menos ingresos por actividades excluidas o no sujetas y otros ingresos no gravados
    row_13_excluded_non_taxable: float = Field(default=0, ge=0)
    
    # Renglón 14: Menos ingresos por actividades exentas en el municipio
    row_14_exempt_income: float = Field(default=0, ge=0)
    
    # Renglón 15: Total ingresos gravables (Calculado: R10 - (R11 + R12 + R13 + R14))
    # CAMPO CALCULADO - No editable
    
    # Campos legacy para compatibilidad
    row_8_ordinary_income: Optional[float] = Field(default=0, ge=0)
    row_9_extraordinary_income: Optional[float] = Field(default=0, ge=0)
    row_11_returns: Optional[float] = Field(default=0, ge=0)
    row_12_exports: Optional[float] = Field(default=0, ge=0)
    row_13_fixed_assets_sales: Optional[float] = Field(default=0, ge=0)
    row_14_excluded_income: Optional[float] = Field(default=0, ge=0)
    row_15_non_taxable_income: Optional[float] = Field(default=0, ge=0)


class IncomeBaseResponse(IncomeBaseSchema):
    """Respuesta con campos calculados."""
    id: int
    declaration_id: int
    
    # Campos calculados (read-only)
    row_10_total_income_municipality: Optional[float] = None
    row_10_total_income: Optional[float] = None  # Alias para compatibilidad
    row_15_taxable_income: Optional[float] = None
    row_16_taxable_income: Optional[float] = None  # Alias para compatibilidad
    
    class Config:
        from_attributes = True


# ===================== ACTIVIDADES - SECCIÓN C =====================

class TaxActivityBase(BaseModel):
    """Catálogo de actividades económicas."""
    ciiu_code: str = Field(..., min_length=1, max_length=10)
    description: str = Field(..., min_length=1, max_length=500)
    tax_rate: float = Field(..., ge=0, le=100)


class TaxActivityCreate(TaxActivityBase):
    municipality_id: int


class TaxActivityResponse(TaxActivityBase):
    id: int
    municipality_id: int
    is_active: bool
    
    class Config:
        from_attributes = True


class TaxableActivityBase(BaseModel):
    """
    Sección C – Discriminación de Ingresos Gravados y Actividades.
    Basado en: Documents/formulario-ICA.md - Sección C
    """
    activity_type: str = Field(default="principal", pattern=r'^(principal|secundaria)$')
    ciiu_code: str = Field(..., min_length=1, max_length=10)
    description: Optional[str] = Field(None, max_length=500)
    income: float = Field(default=0, ge=0)  # Ingresos gravados
    tax_rate: float = Field(default=0, ge=0)  # Tarifa (por mil)
    special_rate: Optional[float] = Field(None, ge=0)  # Tarifa especial (si aplica)


class TaxableActivityCreate(TaxableActivityBase):
    pass


class TaxableActivityResponse(TaxableActivityBase):
    id: int
    declaration_id: int
    generated_tax: Optional[float] = None  # Impuesto ICA calculado
    
    class Config:
        from_attributes = True


# ===================== GENERACIÓN DE ENERGÍA - LEY 56 =====================

class EnergyGenerationBase(BaseModel):
    """
    Generación de energía - Ley 56 de 1981.
    Basado en: Documents/formulario-ICA.md - Sección C, Renglones 18-19
    """
    # Renglón 18: Generación de energía – Capacidad instalada (kW)
    installed_capacity_kw: float = Field(default=0, ge=0)
    
    # Renglón 19: Impuesto Ley 56 de 1981
    law_56_tax: float = Field(default=0, ge=0)


class EnergyGenerationCreate(EnergyGenerationBase):
    pass


class EnergyGenerationResponse(EnergyGenerationBase):
    id: int
    declaration_id: int
    
    class Config:
        from_attributes = True


# ===================== LIQUIDACIÓN - SECCIÓN D =====================

class TaxSettlementBase(BaseModel):
    """
    Sección D – Liquidación del Impuesto.
    Basado en: Documents/formulario-ICA.md - Sección D, Renglones 20-34
    """
    # Renglón 20: Total impuesto de industria y comercio (Calculado: R17 + R19)
    row_20_total_ica_tax: float = Field(default=0, ge=0)
    
    # Renglón 21: Impuesto de avisos y tableros
    row_21_signs_boards: float = Field(default=0, ge=0)
    
    # Renglón 22: Pago por unidades comerciales adicionales del sector financiero
    row_22_financial_additional_units: float = Field(default=0, ge=0)
    
    # Renglón 23: Sobretasa bomberil
    row_23_bomberil_surcharge: float = Field(default=0, ge=0)
    
    # Renglón 24: Sobretasa de seguridad
    row_24_security_surcharge: float = Field(default=0, ge=0)
    
    # Renglón 26: Menos exenciones o exoneraciones sobre el impuesto
    row_26_exemptions: float = Field(default=0, ge=0)
    
    # Renglón 27: Menos retenciones practicadas en el municipio
    row_27_withholdings_municipality: float = Field(default=0, ge=0)
    
    # Renglón 28: Menos autorretenciones practicadas en el municipio
    row_28_self_withholdings: float = Field(default=0, ge=0)
    
    # Renglón 29: Menos anticipo liquidado en el año anterior
    row_29_previous_advance: float = Field(default=0, ge=0)
    
    # Renglón 30: Anticipo del año siguiente
    row_30_next_year_advance: float = Field(default=0, ge=0)
    
    # Renglón 31: Sanciones
    row_31_penalties: float = Field(default=0, ge=0)
    row_31_penalty_type: Optional[str] = Field(None, pattern=r'^(extemporaneidad|correccion|inexactitud|otra)?$')
    row_31_penalty_other_description: Optional[str] = Field(None, max_length=255)
    
    # Renglón 32: Menos saldo a favor del período anterior
    row_32_previous_balance_favor: float = Field(default=0, ge=0)
    
    # Campos legacy para compatibilidad
    row_30_ica_tax: Optional[float] = Field(default=0, ge=0)
    row_31_signs_boards: Optional[float] = Field(default=0, ge=0)
    row_32_surcharge: Optional[float] = Field(default=0, ge=0)


class TaxSettlementResponse(TaxSettlementBase):
    id: int
    declaration_id: int
    row_25_total_tax_payable: Optional[float] = None  # Calculado
    row_33_total_tax: Optional[float] = None  # Legacy calculado
    
    class Config:
        from_attributes = True


# ===================== PAGO - SECCIÓN E =====================

class PaymentSectionBase(BaseModel):
    """
    Sección E – Pago.
    Basado en: Documents/formulario-ICA.md - Sección E, Renglones 35-40
    """
    # Renglón 35: Valor a pagar
    row_35_amount_to_pay: float = Field(default=0, ge=0)
    
    # Renglón 36: Descuento por pronto pago
    row_36_early_payment_discount: float = Field(default=0, ge=0)
    
    # Renglón 37: Intereses de mora
    row_37_late_interest: float = Field(default=0, ge=0)
    
    # Renglón 39: Pago voluntario
    row_39_voluntary_payment: float = Field(default=0, ge=0)
    row_39_voluntary_destination: Optional[str] = Field(None, max_length=255)


class PaymentSectionCreate(PaymentSectionBase):
    pass


class PaymentSectionResponse(PaymentSectionBase):
    id: int
    declaration_id: int
    row_38_total_to_pay: Optional[float] = None  # Calculado: R35 - R36 + R37
    row_40_total_with_voluntary: Optional[float] = None  # Calculado: R38 + R39
    
    class Config:
        from_attributes = True


# ===================== DESCUENTOS - MODELO LEGACY =====================

class DiscountsCreditsBase(BaseModel):
    """
    Modelo legacy para compatibilidad.
    """
    tax_discounts: float = Field(default=0, ge=0)
    advance_payments: float = Field(default=0, ge=0)
    withholdings: float = Field(default=0, ge=0)


class DiscountsCreditsResponse(DiscountsCreditsBase):
    id: int
    declaration_id: int
    total_credits: Optional[float] = None  # Calculado
    
    class Config:
        from_attributes = True


# ===================== RESULTADO - SECCIÓN F (SALDOS) =====================

class DeclarationResultBase(BaseModel):
    """
    Resultado Final – Total a Pagar / Saldo a Favor.
    Validación: Nunca ambos al mismo tiempo.
    """
    amount_to_pay: float = Field(default=0, ge=0)
    balance_in_favor: float = Field(default=0, ge=0)
    
    @validator('balance_in_favor')
    def validate_mutual_exclusion(cls, v, values):
        if v > 0 and values.get('amount_to_pay', 0) > 0:
            raise ValueError('No puede tener valor a pagar y saldo a favor simultáneamente')
        return v


class DeclarationResultResponse(DeclarationResultBase):
    id: int
    declaration_id: int
    
    class Config:
        from_attributes = True


# ===================== FIRMA - SECCIÓN F =====================

class SignatureData(BaseModel):
    """
    Sección F – Firmas Digitales.
    Basado en: Documents/formulario-ICA.md - Sección F
    Una vez firmada la declaración, queda bloqueada para edición.
    """
    # Firma del declarante
    declarant_name: str = Field(..., min_length=2, max_length=255)
    declarant_document: Optional[str] = Field(None, max_length=50)
    declarant_signature_method: str = Field(default="manuscrita", pattern=r'^(manuscrita|clave)$')
    declarant_oath_accepted: bool = Field(default=False)  # Checkbox de declaración bajo juramento
    declaration_date: date
    
    # Firma del contador / revisor fiscal
    requires_fiscal_reviewer: bool = Field(default=False)
    accountant_name: Optional[str] = Field(None, max_length=255)
    accountant_document: Optional[str] = Field(None, max_length=50)
    accountant_professional_card: Optional[str] = Field(None, max_length=50)
    accountant_signature_method: Optional[str] = Field(None, pattern=r'^(manuscrita|clave)?$')
    
    # Firma digital (base64 del canvas si es manuscrita)
    signature_image: Optional[str] = None
    accountant_signature_image: Optional[str] = None
    
    # Legacy field
    professional_card_number: Optional[str] = Field(None, max_length=50)


class SignatureResponse(SignatureData):
    id: int
    signed_at: Optional[datetime] = None
    document_hash: Optional[str] = None
    integrity_verified: bool = False
    
    class Config:
        from_attributes = True


# ===================== DECLARACIÓN ICA COMPLETA =====================

class ICADeclarationCreate(BaseModel):
    """Crear nueva declaración ICA."""
    tax_year: int = Field(..., ge=2000, le=2100)
    declaration_type: DeclarationTypeEnum = DeclarationTypeEnum.INICIAL
    municipality_id: int
    correction_of_id: Optional[int] = None


class ICADeclarationUpdate(BaseModel):
    """Actualizar declaración existente."""
    taxpayer: Optional[TaxpayerBase] = None
    income_base: Optional[IncomeBaseSchema] = None
    activities: Optional[List[TaxableActivityBase]] = None
    energy_generation: Optional[EnergyGenerationBase] = None
    settlement: Optional[TaxSettlementBase] = None
    payment_section: Optional[PaymentSectionBase] = None
    discounts: Optional[DiscountsCreditsBase] = None


class ICADeclarationResponse(BaseModel):
    """Respuesta completa de declaración ICA."""
    id: int
    form_number: Optional[str] = None
    filing_number: Optional[str] = None  # Número de radicado
    tax_year: int
    filing_date: Optional[datetime] = None  # Fecha de presentación
    declaration_type: DeclarationTypeEnum
    status: FormStatusEnum
    
    user_id: int
    municipality_id: int
    
    # Corrección
    correction_of_id: Optional[int] = None  # ID de la declaración original si es corrección
    has_been_corrected: bool = False  # True si ya se generó una corrección
    
    is_signed: bool
    signed_at: Optional[datetime]
    integrity_hash: Optional[str]
    
    pdf_path: Optional[str]
    pdf_generated_at: Optional[datetime]
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime]
    
    # Secciones del formulario
    taxpayer: Optional[TaxpayerResponse] = None
    income_base: Optional[IncomeBaseResponse] = None
    activities: List[TaxableActivityResponse] = []
    energy_generation: Optional[EnergyGenerationResponse] = None
    settlement: Optional[TaxSettlementResponse] = None
    payment_section: Optional[PaymentSectionResponse] = None
    discounts: Optional[DiscountsCreditsResponse] = None
    result: Optional[DeclarationResultResponse] = None
    
    class Config:
        from_attributes = True


# ===================== CÁLCULO =====================

class CalculationRequest(BaseModel):
    """Solicitud de cálculo automático."""
    income_base: IncomeBaseSchema
    activities: List[TaxableActivityBase]
    settlement: TaxSettlementBase
    discounts: DiscountsCreditsBase


class CalculationResponse(BaseModel):
    """Resultado del cálculo automático."""
    row_10_total_income: float
    row_16_taxable_income: float
    total_activities_tax: float
    row_33_total_tax: float
    total_credits: float
    amount_to_pay: float
    balance_in_favor: float
