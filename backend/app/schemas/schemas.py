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


# ===================== ENUMS =====================

class UserRoleEnum(str, Enum):
    DECLARANTE = "declarante"
    ADMIN_ALCALDIA = "admin_alcaldia"
    ADMIN_SISTEMA = "admin_sistema"


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
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def password_strength(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    role: UserRoleEnum
    is_active: bool
    municipality_id: Optional[int]
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


class WhiteLabelConfigUpdate(WhiteLabelConfigBase):
    pass


class WhiteLabelConfigResponse(WhiteLabelConfigBase):
    id: int
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ===================== CONTRIBUYENTE - SECCIÓN A =====================

class TaxpayerBase(BaseModel):
    """
    Sección A – Información del Contribuyente.
    3.1 Identificación + 3.2 Ubicación
    """
    # 3.1 Identificación
    document_type: str = Field(..., min_length=1, max_length=20)
    document_number: str = Field(..., min_length=1, max_length=50)
    verification_digit: Optional[str] = Field(None, max_length=1)
    legal_name: str = Field(..., min_length=2, max_length=255)
    
    # 3.2 Ubicación
    address: Optional[str] = Field(None, max_length=500)
    municipality: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    
    @validator('document_number')
    def validate_document(cls, v):
        # Sanitización contra SQL Injection
        if re.search(r'[;\'"\\]', v):
            raise ValueError('Caracteres no permitidos en número de documento')
        return v


class TaxpayerCreate(TaxpayerBase):
    pass


class TaxpayerResponse(TaxpayerBase):
    id: int
    declaration_id: int
    
    class Config:
        from_attributes = True


# ===================== BASE GRAVABLE - SECCIÓN B =====================

class IncomeBaseSchema(BaseModel):
    """
    Sección B – Base Gravable.
    Renglones 8-16 según formulario ICA.
    """
    # Campos editables
    row_8_ordinary_income: float = Field(default=0, ge=0)
    row_9_extraordinary_income: float = Field(default=0, ge=0)
    row_11_returns: float = Field(default=0, ge=0)
    row_12_exports: float = Field(default=0, ge=0)
    row_13_fixed_assets_sales: float = Field(default=0, ge=0)
    row_14_excluded_income: float = Field(default=0, ge=0)
    row_15_non_taxable_income: float = Field(default=0, ge=0)


class IncomeBaseResponse(IncomeBaseSchema):
    """Respuesta con campos calculados."""
    id: int
    declaration_id: int
    
    # Campos calculados (read-only)
    row_10_total_income: float
    row_16_taxable_income: float
    
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
    Sección C – Actividades Gravadas.
    Por cada actividad del contribuyente.
    """
    ciiu_code: str = Field(..., min_length=1, max_length=10)
    description: Optional[str] = Field(None, max_length=500)
    income: float = Field(default=0, ge=0)
    tax_rate: float = Field(default=0, ge=0)


class TaxableActivityCreate(TaxableActivityBase):
    pass


class TaxableActivityResponse(TaxableActivityBase):
    id: int
    declaration_id: int
    generated_tax: float  # Campo calculado
    
    class Config:
        from_attributes = True


# ===================== LIQUIDACIÓN - SECCIÓN D =====================

class TaxSettlementBase(BaseModel):
    """
    Sección D – Liquidación del Impuesto.
    Renglones 30-33.
    """
    row_30_ica_tax: float = Field(default=0, ge=0)
    row_31_signs_boards: float = Field(default=0, ge=0)
    row_32_surcharge: float = Field(default=0, ge=0)


class TaxSettlementResponse(TaxSettlementBase):
    id: int
    declaration_id: int
    row_33_total_tax: float  # Calculado
    
    class Config:
        from_attributes = True


# ===================== DESCUENTOS - SECCIÓN E =====================

class DiscountsCreditsBase(BaseModel):
    """
    Sección E – Descuentos, Créditos y Anticipos.
    """
    tax_discounts: float = Field(default=0, ge=0)
    advance_payments: float = Field(default=0, ge=0)
    withholdings: float = Field(default=0, ge=0)


class DiscountsCreditsResponse(DiscountsCreditsBase):
    id: int
    declaration_id: int
    total_credits: float  # Calculado
    
    class Config:
        from_attributes = True


# ===================== RESULTADO - SECCIÓN F =====================

class DeclarationResultBase(BaseModel):
    """
    Sección F – Total a Pagar / Saldo a Favor.
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


# ===================== FIRMA - SECCIÓN G =====================

class SignatureData(BaseModel):
    """
    Sección G – Firma y Responsabilidad.
    Datos para firma digital.
    """
    declarant_name: str = Field(..., min_length=2, max_length=255)
    declaration_date: date
    accountant_name: Optional[str] = Field(None, max_length=255)
    professional_card_number: Optional[str] = Field(None, max_length=50)
    signature_image: str  # Base64 del canvas


class SignatureResponse(SignatureData):
    id: int
    signed_at: datetime
    
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
    settlement: Optional[TaxSettlementBase] = None
    discounts: Optional[DiscountsCreditsBase] = None


class ICADeclarationResponse(BaseModel):
    """Respuesta completa de declaración ICA."""
    id: int
    form_number: str
    tax_year: int
    declaration_type: DeclarationTypeEnum
    status: FormStatusEnum
    
    user_id: int
    municipality_id: int
    
    is_signed: bool
    signed_at: Optional[datetime]
    integrity_hash: Optional[str]
    
    pdf_path: Optional[str]
    pdf_generated_at: Optional[datetime]
    
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Secciones del formulario
    taxpayer: Optional[TaxpayerResponse] = None
    income_base: Optional[IncomeBaseResponse] = None
    activities: List[TaxableActivityResponse] = []
    settlement: Optional[TaxSettlementResponse] = None
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
