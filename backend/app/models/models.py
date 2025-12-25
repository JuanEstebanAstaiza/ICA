"""
Modelos de base de datos para el sistema ICA.
Basado en: Documents/formulario-ICA.md

Modelo de Datos Base (sección 10.3):
{
  "periodo": "YYYY",
  "municipio": "string",
  "contribuyente": {},
  "ingresos": {},
  "actividades": [],
  "liquidacion": {},
  "resultado": {}
}
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    ForeignKey, Text, Enum, JSON, Date, LargeBinary
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..db.database import Base
import enum


class UserRole(enum.Enum):
    """Roles de usuario según requerimientos."""
    DECLARANTE = "declarante"  # Usuario declarante
    ADMIN_ALCALDIA = "admin_alcaldia"  # Administrador de alcaldía
    ADMIN_SISTEMA = "admin_sistema"  # Administrador del sistema


class PersonType(enum.Enum):
    """Tipo de persona para registro de declarantes."""
    NATURAL = "natural"  # Persona natural
    JURIDICA = "juridica"  # Persona jurídica (empresa)


class DeclarationType(enum.Enum):
    """
    Tipos de declaración - Sección 2 del formulario ICA.
    Campo de selección única.
    """
    INICIAL = "inicial"
    CORRECCION = "correccion"
    CORRECCION_DISMINUYE = "correccion_disminuye"
    CORRECCION_AUMENTA = "correccion_aumenta"


class FormStatus(enum.Enum):
    """Estado del formulario."""
    BORRADOR = "borrador"
    COMPLETADO = "completado"
    FIRMADO = "firmado"
    ANULADO = "anulado"


# ===================== MODELOS DE USUARIO =====================

class User(Base):
    """
    Modelo de usuario con autenticación.
    Soporta roles: declarante, admin_alcaldia, admin_sistema.
    Soporta personas naturales y jurídicas.
    
    Para PERSONA NATURAL:
    - Se usan los campos: full_name, document_type, document_number, email, phone, address
    
    Para PERSONA JURÍDICA:
    - Datos de la empresa: company_name, nit, nit_verification_digit, company_address
    - Datos del representante legal: full_name, document_type, document_number, email, phone
    - El login se hace con el email del representante legal
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Tipo de persona (natural o jurídica)
    person_type = Column(Enum(PersonType), default=PersonType.NATURAL)
    
    # ===== DATOS DE PERSONA NATURAL / REPRESENTANTE LEGAL =====
    full_name = Column(String(255), nullable=False)  # Nombre completo
    document_type = Column(String(50))  # CC, CE, Pasaporte, etc.
    document_number = Column(String(50), index=True)  # Número de documento
    phone = Column(String(50))  # Teléfono de contacto
    address = Column(String(500))  # Dirección (autocompletada con municipio de la plataforma)
    
    # ===== DATOS DE PERSONA JURÍDICA (solo si person_type == JURIDICA) =====
    company_name = Column(String(255))  # Razón social
    nit = Column(String(20), index=True)  # NIT de la empresa
    nit_verification_digit = Column(String(1))  # Dígito de verificación del NIT
    company_address = Column(String(500))  # Dirección de la empresa
    company_phone = Column(String(50))  # Teléfono de la empresa
    company_email = Column(String(255))  # Email corporativo
    economic_activity = Column(String(255))  # Actividad económica principal
    
    # Rol y permisos
    role = Column(Enum(UserRole), default=UserRole.DECLARANTE)
    is_active = Column(Boolean, default=True)
    
    # Relación con alcaldía/municipio
    municipality_id = Column(Integer, ForeignKey("municipalities.id"))
    
    # Auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relaciones
    municipality = relationship("Municipality", back_populates="users")
    declarations = relationship("ICADeclaration", back_populates="user", foreign_keys="[ICADeclaration.user_id]")


# ===================== MODELOS DE ALCALDÍA =====================

class Municipality(Base):
    """
    Modelo de municipio/alcaldía.
    Cada alcaldía tiene su configuración marca blanca.
    """
    __tablename__ = "municipalities"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True)  # Código DANE
    name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    
    # Configuración marca blanca
    config_id = Column(Integer, ForeignKey("white_label_configs.id"))
    
    # Estado
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    users = relationship("User", back_populates="municipality")
    config = relationship("WhiteLabelConfig", back_populates="municipality")
    declarations = relationship("ICADeclaration", back_populates="municipality")
    activities = relationship("TaxActivity", back_populates="municipality")
    formula_parameters = relationship("FormulaParameters", back_populates="municipality", uselist=False)


class WhiteLabelConfig(Base):
    """
    Configuración marca blanca por alcaldía.
    Panel administrativo para personalización.
    """
    __tablename__ = "white_label_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identidad visual
    logo_path = Column(String(500))
    primary_color = Column(String(7), default="#003366")
    secondary_color = Column(String(7), default="#0066CC")
    accent_color = Column(String(7), default="#FF9900")
    
    # Tipografía
    font_family = Column(String(100), default="Arial, sans-serif")
    
    # Textos personalizables
    header_text = Column(Text)
    footer_text = Column(Text)
    legal_notes = Column(Text)
    
    # Configuración del formulario
    form_title = Column(String(500), default="Formulario Único Nacional de Declaración y Pago ICA")
    
    # Marca de agua para PDF (prevención de fraudes)
    watermark_text = Column(String(255), default="")  # Nombre de la alcaldía como marca de agua
    
    # Configuración de Numeración (Consecutivo y Radicado)
    # Consecutivo: número secuencial del formulario dentro del municipio
    consecutivo_prefijo = Column(String(10), default="")  # Prefijo opcional
    consecutivo_actual = Column(Integer, default=1)  # Número actual
    consecutivo_digitos = Column(Integer, default=12)  # Cantidad de dígitos (relleno con ceros)
    
    # Radicado: número de radicación oficial después de firma
    radicado_prefijo = Column(String(10), default="")  # Prefijo opcional
    radicado_actual = Column(Integer, default=1)  # Número actual
    radicado_digitos = Column(Integer, default=16)  # Cantidad de dígitos (relleno con ceros)
    
    # Metadatos
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"))
    
    # Relación
    municipality = relationship("Municipality", back_populates="config", uselist=False)


class FormulaParameters(Base):
    """
    Parámetros configurables de fórmulas por municipio.
    Permite edición en caliente de valores numéricos de las fórmulas
    en caso de cambios en legislación.
    Basado en: Documents/formulario-ICA.md - Sección D y E
    """
    __tablename__ = "formula_parameters"
    
    id = Column(Integer, primary_key=True, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False, unique=True)
    
    # Parámetros de Avisos y Tableros (Sección D - Renglón 21)
    avisos_tableros_porcentaje = Column(Float, default=15.0)  # % sobre impuesto ICA (típicamente 15%)
    
    # Parámetros de Sobretasa Bomberil (Sección D - Renglón 23)
    sobretasa_bomberil_porcentaje = Column(Float, default=0.0)  # % sobre impuesto ICA
    
    # Parámetros de Sobretasa Seguridad (Sección D - Renglón 24)
    sobretasa_seguridad_porcentaje = Column(Float, default=0.0)  # % sobre impuesto ICA
    
    # Parámetros Ley 56 de 1981 - Generación de energía (Sección D - Renglón 19)
    ley_56_tarifa_por_kw = Column(Float, default=0.0)  # Tarifa por kW instalado
    
    # Parámetros de Anticipo (Sección D - Renglón 30)
    anticipo_ano_siguiente_porcentaje = Column(Float, default=40.0)  # % típico de anticipo
    
    # Parámetros de Descuento por Pronto Pago (Sección E - Renglón 36)
    descuento_pronto_pago_porcentaje = Column(Float, default=10.0)  # % descuento
    descuento_pronto_pago_dias = Column(Integer, default=30)  # Días para aplicar descuento
    
    # Parámetros de Intereses de Mora (Sección E - Renglón 37)
    interes_mora_mensual = Column(Float, default=1.0)  # % mensual de mora
    
    # Parámetros de Unidades Comerciales Adicionales Sector Financiero (Sección D - Renglón 22)
    unidades_adicionales_financiero_valor = Column(Float, default=0.0)
    
    # Metadatos
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"))
    
    # Relación
    municipality = relationship("Municipality", back_populates="formula_parameters")


# ===================== MODELOS DEL FORMULARIO ICA =====================

class ICADeclaration(Base):
    """
    Declaración ICA principal.
    Basado en: Documents/formulario-ICA.md - Metadatos del Formulario (Sistema)
    """
    __tablename__ = "ica_declarations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Sección 0 - Metadatos del Formulario (Sistema)
    tax_year = Column(Integer, nullable=False)  # Periodo gravable (YYYY)
    filing_date = Column(DateTime(timezone=True))  # Fecha de presentación (ISO-8601)
    declaration_type = Column(Enum(DeclarationType), default=DeclarationType.INICIAL)  # Tipo de declaración
    form_number = Column(String(50), unique=True, index=True)  # Consecutivo del formulario (único)
    filing_number = Column(String(50), unique=True, index=True)  # Número de radicado (único, posterior a firma)
    status = Column(Enum(FormStatus), default=FormStatus.BORRADOR)  # Estado de la declaración
    
    # Usuario y alcaldía
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False)
    
    # Corrección (si aplica)
    correction_of_id = Column(Integer, ForeignKey("ica_declarations.id"))
    
    # Firma digital
    is_signed = Column(Boolean, default=False)
    signature_data = Column(Text)  # Base64 de firma canvas
    signed_at = Column(DateTime(timezone=True))
    signed_by_user_id = Column(Integer, ForeignKey("users.id"))
    integrity_hash = Column(String(64))  # SHA-256
    
    # PDF generado
    pdf_path = Column(String(500))
    pdf_generated_at = Column(DateTime(timezone=True))
    
    # Auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    user = relationship("User", back_populates="declarations", foreign_keys=[user_id])
    municipality = relationship("Municipality", back_populates="declarations")
    taxpayer = relationship("Taxpayer", back_populates="declaration", uselist=False)
    income_base = relationship("IncomeBase", back_populates="declaration", uselist=False)
    activities = relationship("TaxableActivity", back_populates="declaration")
    energy_generation = relationship("EnergyGeneration", back_populates="declaration", uselist=False)
    settlement = relationship("TaxSettlement", back_populates="declaration", uselist=False)
    payment_section = relationship("PaymentSection", back_populates="declaration", uselist=False)
    discounts = relationship("DiscountsCredits", back_populates="declaration", uselist=False)
    result = relationship("DeclarationResult", back_populates="declaration", uselist=False)
    signature_info = relationship("SignatureInfo", back_populates="declaration", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="declaration")


class Taxpayer(Base):
    """
    Información del Contribuyente - Sección A del formulario ICA.
    Basado en: Documents/formulario-ICA.md - Sección A
    """
    __tablename__ = "taxpayers"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # Renglón 1: Identificación
    legal_name = Column(String(255), nullable=False)  # Apellidos y nombres / Razón social
    
    # Tipo de entidad (según formulario-ICA.md)
    entity_type = Column(String(20), default="privada")  # privada | publica
    
    # Renglón 2: Cédula o NIT
    document_type = Column(String(20), nullable=False)
    document_number = Column(String(50), nullable=False)
    verification_digit = Column(String(1))  # Dígito de verificación (DV)
    
    # Renglón 3: Dirección de notificación
    address = Column(String(500))
    notification_department = Column(String(255))  # Departamento de notificación
    notification_municipality = Column(String(255))  # Municipio de notificación
    
    # Renglón 4: Teléfono
    phone = Column(String(50))
    
    # Renglón 5: Correo electrónico
    email = Column(String(255))
    
    # Renglón 6: Número de establecimientos en el municipio
    num_establishments = Column(Integer, default=1)
    
    # Renglón 7: Clasificación del contribuyente (según formulario-ICA.md)
    taxpayer_classification = Column(String(30), default="comun")  # comun | simplificado
    
    # Campos legacy para compatibilidad
    municipality = Column(String(255))  # Alias de notification_municipality
    department = Column(String(255))  # Alias de notification_department
    
    # Relación
    declaration = relationship("ICADeclaration", back_populates="taxpayer")


class IncomeBase(Base):
    """
    Base Gravable - Sección B del formulario ICA.
    Contiene renglones 8-15 según Documents/formulario-ICA.md
    """
    __tablename__ = "income_bases"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # Sección B - Base Gravable (según formulario-ICA.md)
    # Renglón 8: Total ingresos ordinarios y extraordinarios del período en todo el país
    row_8_total_income_country = Column(Float, default=0)
    
    # Renglón 9: Menos ingresos fuera del municipio
    row_9_income_outside_municipality = Column(Float, default=0)
    
    # Renglón 10: Total ingresos ordinarios y extraordinarios en el municipio (Calculado: R8 - R9)
    # CAMPO CALCULADO
    
    # Renglón 11: Menos ingresos por devoluciones, rebajas y descuentos
    row_11_returns_rebates_discounts = Column(Float, default=0)
    
    # Renglón 12: Menos ingresos por exportaciones y venta de activos fijos
    row_12_exports_fixed_assets = Column(Float, default=0)
    
    # Renglón 13: Menos ingresos por actividades excluidas o no sujetas y otros ingresos no gravados
    row_13_excluded_non_taxable = Column(Float, default=0)
    
    # Renglón 14: Menos ingresos por actividades exentas en el municipio
    row_14_exempt_income = Column(Float, default=0)
    
    # Renglón 15: Total ingresos gravables (Calculado: R10 - (R11 + R12 + R13 + R14))
    # CAMPO CALCULADO
    
    # Campos legacy para compatibilidad hacia atrás
    row_8_ordinary_income = Column(Float, default=0)
    row_9_extraordinary_income = Column(Float, default=0)
    row_11_returns = Column(Float, default=0)
    row_12_exports = Column(Float, default=0)
    row_13_fixed_assets_sales = Column(Float, default=0)
    row_14_excluded_income = Column(Float, default=0)
    row_15_non_taxable_income = Column(Float, default=0)
    
    @property
    def row_10_total_income_municipality(self) -> float:
        """Renglón 10: Total ingresos en el municipio = R8 - R9"""
        return (self.row_8_total_income_country or 0) - (self.row_9_income_outside_municipality or 0)
    
    @property
    def row_10_total_income(self) -> float:
        """Alias para compatibilidad: Renglón 10"""
        return self.row_10_total_income_municipality
    
    @property
    def row_15_taxable_income(self) -> float:
        """
        Renglón 15: Total ingresos gravables.
        Fórmula: R10 - (R11 + R12 + R13 + R14)
        """
        deductions = (
            (self.row_11_returns_rebates_discounts or 0) +
            (self.row_12_exports_fixed_assets or 0) +
            (self.row_13_excluded_non_taxable or 0) +
            (self.row_14_exempt_income or 0)
        )
        return max(0, self.row_10_total_income_municipality - deductions)
    
    @property
    def row_16_taxable_income(self) -> float:
        """Alias para compatibilidad: Renglón 15 (antes era 16)"""
        return self.row_15_taxable_income
    
    # Relación
    declaration = relationship("ICADeclaration", back_populates="income_base")


class TaxActivity(Base):
    """
    Catálogo de actividades económicas por municipio.
    Con código CIIU y tarifas.
    """
    __tablename__ = "tax_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False)
    
    ciiu_code = Column(String(10), nullable=False)  # Código CIIU
    description = Column(String(500), nullable=False)
    tax_rate = Column(Float, nullable=False)  # Tarifa ICA (por mil)
    
    is_active = Column(Boolean, default=True)
    
    # Relación
    municipality = relationship("Municipality", back_populates="activities")


class TaxableActivity(Base):
    """
    Actividades Gravadas - Sección C del formulario ICA.
    Discriminación de ingresos gravados y actividades.
    Basado en: Documents/formulario-ICA.md - Sección C
    """
    __tablename__ = "taxable_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # Datos de la actividad (según formulario-ICA.md)
    activity_type = Column(String(20), default="principal")  # principal | secundaria
    ciiu_code = Column(String(10), nullable=False)  # Código CIIU
    description = Column(String(500))
    income = Column(Float, default=0)  # Ingresos gravados
    tax_rate = Column(Float, default=0)  # Tarifa (por mil)
    special_rate = Column(Float, nullable=True)  # Tarifa especial (si aplica)
    
    @property
    def generated_tax(self) -> float:
        """Impuesto ICA = ingresos * tarifa / 1000"""
        rate = self.special_rate if self.special_rate else self.tax_rate
        return (self.income or 0) * (rate or 0) / 1000
    
    # Relación
    declaration = relationship("ICADeclaration", back_populates="activities")


class EnergyGeneration(Base):
    """
    Generación de energía - Ley 56 de 1981.
    Basado en: Documents/formulario-ICA.md - Sección C, Renglones 18-19
    """
    __tablename__ = "energy_generation"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # Renglón 18: Generación de energía – Capacidad instalada (kW)
    installed_capacity_kw = Column(Float, default=0)
    
    # Renglón 19: Impuesto Ley 56 de 1981 (calculado según parámetros municipio)
    law_56_tax = Column(Float, default=0)
    
    # Relación
    declaration = relationship("ICADeclaration", back_populates="energy_generation")


class TaxSettlement(Base):
    """
    Liquidación del Impuesto - Sección D del formulario ICA.
    Basado en: Documents/formulario-ICA.md - Sección D, Renglones 20-34
    """
    __tablename__ = "tax_settlements"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # Renglón 20: Total impuesto de industria y comercio (Calculado: R17 + R19)
    row_20_total_ica_tax = Column(Float, default=0)
    
    # Renglón 21: Impuesto de avisos y tableros
    row_21_signs_boards = Column(Float, default=0)
    
    # Renglón 22: Pago por unidades comerciales adicionales del sector financiero
    row_22_financial_additional_units = Column(Float, default=0)
    
    # Renglón 23: Sobretasa bomberil
    row_23_bomberil_surcharge = Column(Float, default=0)
    
    # Renglón 24: Sobretasa de seguridad
    row_24_security_surcharge = Column(Float, default=0)
    
    # Renglón 25: Total impuesto a cargo (Calculado: R20 + R21 + R22 + R23 + R24)
    # CAMPO CALCULADO
    
    # Renglón 26: Menos exenciones o exoneraciones sobre el impuesto
    row_26_exemptions = Column(Float, default=0)
    
    # Renglón 27: Menos retenciones practicadas en el municipio
    row_27_withholdings_municipality = Column(Float, default=0)
    
    # Renglón 28: Menos autorretenciones practicadas en el municipio
    row_28_self_withholdings = Column(Float, default=0)
    
    # Renglón 29: Menos anticipo liquidado en el año anterior
    row_29_previous_advance = Column(Float, default=0)
    
    # Renglón 30: Anticipo del año siguiente
    row_30_next_year_advance = Column(Float, default=0)
    
    # Renglón 31: Sanciones
    row_31_penalties = Column(Float, default=0)
    row_31_penalty_type = Column(String(50))  # extemporaneidad | correccion | inexactitud | otra
    row_31_penalty_other_description = Column(String(255))
    
    # Renglón 32: Menos saldo a favor del período anterior
    row_32_previous_balance_favor = Column(Float, default=0)
    
    # Renglón 33: Total saldo a cargo (Calculado)
    # CAMPO CALCULADO
    
    # Renglón 34: Total saldo a favor (Calculado)
    # CAMPO CALCULADO
    
    # Campos legacy para compatibilidad
    row_30_ica_tax = Column(Float, default=0)
    row_31_signs_boards = Column(Float, default=0)
    row_32_surcharge = Column(Float, default=0)
    
    @property
    def row_25_total_tax_payable(self) -> float:
        """Renglón 25: Total impuesto a cargo = R20 + R21 + R22 + R23 + R24"""
        return (
            (self.row_20_total_ica_tax or 0) +
            (self.row_21_signs_boards or 0) +
            (self.row_22_financial_additional_units or 0) +
            (self.row_23_bomberil_surcharge or 0) +
            (self.row_24_security_surcharge or 0)
        )
    
    @property
    def row_33_total_tax(self) -> float:
        """Renglón 33 legacy: Total impuesto = R30 + R31 + R32"""
        return (self.row_30_ica_tax or 0) + (self.row_31_signs_boards or 0) + (self.row_32_surcharge or 0)
    
    # Relación
    declaration = relationship("ICADeclaration", back_populates="settlement")


class PaymentSection(Base):
    """
    Sección E - Pago del formulario ICA.
    Basado en: Documents/formulario-ICA.md - Sección E, Renglones 35-40
    """
    __tablename__ = "payment_sections"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # Renglón 35: Valor a pagar
    row_35_amount_to_pay = Column(Float, default=0)
    
    # Renglón 36: Descuento por pronto pago
    row_36_early_payment_discount = Column(Float, default=0)
    
    # Renglón 37: Intereses de mora
    row_37_late_interest = Column(Float, default=0)
    
    # Renglón 38: Total a pagar (Calculado: R35 - R36 + R37)
    # CAMPO CALCULADO
    
    # Renglón 39: Pago voluntario
    row_39_voluntary_payment = Column(Float, default=0)
    row_39_voluntary_destination = Column(String(255))  # Destino del aporte
    
    # Renglón 40: Total a pagar con pago voluntario (Calculado: R38 + R39)
    # CAMPO CALCULADO
    
    @property
    def row_38_total_to_pay(self) -> float:
        """Renglón 38: Total a pagar = R35 - R36 + R37"""
        return (self.row_35_amount_to_pay or 0) - (self.row_36_early_payment_discount or 0) + (self.row_37_late_interest or 0)
    
    @property
    def row_40_total_with_voluntary(self) -> float:
        """Renglón 40: Total a pagar con pago voluntario = R38 + R39"""
        return self.row_38_total_to_pay + (self.row_39_voluntary_payment or 0)
    
    # Relación
    declaration = relationship("ICADeclaration", back_populates="payment_section")


class DiscountsCredits(Base):
    """
    Descuentos, Créditos y Anticipos - Modelo legacy para compatibilidad.
    """
    __tablename__ = "discounts_credits"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # Campos editables
    tax_discounts = Column(Float, default=0)  # Descuentos tributarios
    advance_payments = Column(Float, default=0)  # Anticipos pagados
    withholdings = Column(Float, default=0)  # Retenciones sufridas
    
    @property
    def total_credits(self) -> float:
        """Total de créditos = descuentos + anticipos + retenciones"""
        return (self.tax_discounts or 0) + (self.advance_payments or 0) + (self.withholdings or 0)
    
    # Relación
    declaration = relationship("ICADeclaration", back_populates="discounts")


class DeclarationResult(Base):
    """
    Total a Pagar / Saldo a Favor - Sección F del formulario ICA.
    Validación: Nunca ambos al mismo tiempo.
    """
    __tablename__ = "declaration_results"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # Solo uno de estos campos debe tener valor > 0
    amount_to_pay = Column(Float, default=0)  # Total a pagar
    balance_in_favor = Column(Float, default=0)  # Saldo a favor
    
    # Relación
    declaration = relationship("ICADeclaration", back_populates="result")


class SignatureInfo(Base):
    """
    Sección F - Firmas Digitales del formulario ICA.
    Basado en: Documents/formulario-ICA.md - Sección F
    Una vez firmada la declaración, queda bloqueada para edición.
    """
    __tablename__ = "signature_info"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # Firma del declarante
    declarant_name = Column(String(255))
    declarant_document = Column(String(50))
    declarant_signature_method = Column(String(30))  # manuscrita | clave
    declarant_signature_image = Column(Text)  # Base64 del canvas si es manuscrita
    declarant_oath_accepted = Column(Boolean, default=False)  # Checkbox de declaración bajo juramento
    declaration_date = Column(Date)
    
    # Firma del contador / revisor fiscal
    requires_fiscal_reviewer = Column(Boolean, default=False)  # Aplica revisor fiscal (Sí / No)
    accountant_name = Column(String(255))
    accountant_document = Column(String(50))
    accountant_professional_card = Column(String(50))  # Tarjeta profesional
    accountant_signature_method = Column(String(30))  # manuscrita | clave
    accountant_signature_image = Column(Text)  # Base64 del canvas si es manuscrita
    
    # Metadatos de firma (NO visibles según formulario-ICA.md)
    document_hash = Column(String(64))  # Hash del documento (SHA-256)
    signed_at = Column(DateTime(timezone=True))  # Fecha y hora
    ip_address = Column(String(50))  # IP
    user_agent = Column(String(500))  # User-Agent
    integrity_verified = Column(Boolean, default=False)  # Integridad verificada
    
    # Legacy field
    professional_card_number = Column(String(50))  # Alias para compatibilidad
    signature_image = Column(Text)  # Alias para compatibilidad
    
    # Relación
    declaration = relationship("ICADeclaration", back_populates="signature_info")


# ===================== MODELO DE AUDITORÍA =====================

class AuditLog(Base):
    """
    Log de auditoría para todas las operaciones.
    Requerimiento: Logs de auditoría.
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Contexto
    user_id = Column(Integer, ForeignKey("users.id"))
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"))
    
    # Acción
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, SIGN, DOWNLOAD
    entity_type = Column(String(100))
    entity_id = Column(Integer)
    
    # Datos
    old_values = Column(JSON)
    new_values = Column(JSON)
    
    # Metadatos
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    declaration = relationship("ICADeclaration", back_populates="audit_logs")
