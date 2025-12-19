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
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Datos personales
    full_name = Column(String(255), nullable=False)
    document_type = Column(String(50))
    document_number = Column(String(50), index=True)
    phone = Column(String(50))
    
    # Rol y permisos
    role = Column(Enum(UserRole), default=UserRole.DECLARANTE)
    is_active = Column(Boolean, default=True)
    
    # Relación con alcaldía
    municipality_id = Column(Integer, ForeignKey("municipalities.id"))
    
    # Auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relaciones
    municipality = relationship("Municipality", back_populates="users")
    declarations = relationship("ICADeclaration", back_populates="user")


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
    
    # Metadatos
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"))
    
    # Relación
    municipality = relationship("Municipality", back_populates="config", uselist=False)


# ===================== MODELOS DEL FORMULARIO ICA =====================

class ICADeclaration(Base):
    """
    Declaración ICA principal.
    Basado en: Documents/formulario-ICA.md - Metadatos Generales
    """
    __tablename__ = "ica_declarations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Metadatos Generales (Sección 1)
    tax_year = Column(Integer, nullable=False)  # Año gravable
    declaration_type = Column(Enum(DeclarationType), default=DeclarationType.INICIAL)
    status = Column(Enum(FormStatus), default=FormStatus.BORRADOR)
    
    # Usuario y alcaldía
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False)
    
    # Número de formulario
    form_number = Column(String(50), unique=True, index=True)
    
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
    settlement = relationship("TaxSettlement", back_populates="declaration", uselist=False)
    discounts = relationship("DiscountsCredits", back_populates="declaration", uselist=False)
    result = relationship("DeclarationResult", back_populates="declaration", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="declaration")


class Taxpayer(Base):
    """
    Información del Contribuyente - Sección A del formulario ICA.
    Secciones 3.1 (Identificación) y 3.2 (Ubicación)
    """
    __tablename__ = "taxpayers"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # 3.1 Identificación
    document_type = Column(String(20), nullable=False)
    document_number = Column(String(50), nullable=False)
    verification_digit = Column(String(1))  # Dígito de verificación
    legal_name = Column(String(255), nullable=False)  # Razón social / Nombre completo
    
    # 3.2 Ubicación
    address = Column(String(500))
    municipality = Column(String(255))
    department = Column(String(255))
    phone = Column(String(50))
    email = Column(String(255))
    
    # Relación
    declaration = relationship("ICADeclaration", back_populates="taxpayer")


class IncomeBase(Base):
    """
    Base Gravable - Sección B del formulario ICA.
    Contiene renglones 8-16 según Documents/formulario-ICA.md
    """
    __tablename__ = "income_bases"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # Renglones Base (editables)
    row_8_ordinary_income = Column(Float, default=0)  # Total ingresos ordinarios
    row_9_extraordinary_income = Column(Float, default=0)  # Ingresos extraordinarios
    row_11_returns = Column(Float, default=0)  # Devoluciones
    row_12_exports = Column(Float, default=0)  # Exportaciones
    row_13_fixed_assets_sales = Column(Float, default=0)  # Ventas de activos fijos
    row_14_excluded_income = Column(Float, default=0)  # Ingresos excluidos
    row_15_non_taxable_income = Column(Float, default=0)  # Ingresos no gravados
    
    # Campos calculados (NO editables)
    # row_10 = row_8 + row_9
    # row_16 = row_10 - (row_11 + row_12 + row_13 + row_14 + row_15)
    
    @property
    def row_10_total_income(self) -> float:
        """Renglón 10: Total ingresos = R8 + R9"""
        return self.row_8_ordinary_income + self.row_9_extraordinary_income
    
    @property
    def row_16_taxable_income(self) -> float:
        """
        Renglón 16: Total ingresos gravables.
        Fórmula: R10 - (R11 + R12 + R13 + R14 + R15)
        """
        deductions = (
            self.row_11_returns +
            self.row_12_exports +
            self.row_13_fixed_assets_sales +
            self.row_14_excluded_income +
            self.row_15_non_taxable_income
        )
        return self.row_10_total_income - deductions
    
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
    Por cada actividad del contribuyente.
    """
    __tablename__ = "taxable_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # Datos de la actividad
    ciiu_code = Column(String(10), nullable=False)
    description = Column(String(500))
    income = Column(Float, default=0)  # Ingresos asociados
    tax_rate = Column(Float, default=0)  # Tarifa ICA
    
    @property
    def generated_tax(self) -> float:
        """Impuesto generado = ingresos * tarifa / 1000"""
        return self.income * self.tax_rate / 1000
    
    # Relación
    declaration = relationship("ICADeclaration", back_populates="activities")


class TaxSettlement(Base):
    """
    Liquidación del Impuesto - Sección D del formulario ICA.
    Renglones 30-33.
    """
    __tablename__ = "tax_settlements"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # Renglón 30: Impuesto de Industria y Comercio (calculado de actividades)
    row_30_ica_tax = Column(Float, default=0)
    
    # Renglón 31: Avisos y Tableros (editable)
    row_31_signs_boards = Column(Float, default=0)
    
    # Renglón 32: Sobretasa (editable)
    row_32_surcharge = Column(Float, default=0)
    
    @property
    def row_33_total_tax(self) -> float:
        """Renglón 33: Total impuesto = R30 + R31 + R32"""
        return self.row_30_ica_tax + self.row_31_signs_boards + self.row_32_surcharge
    
    # Relación
    declaration = relationship("ICADeclaration", back_populates="settlement")


class DiscountsCredits(Base):
    """
    Descuentos, Créditos y Anticipos - Sección E del formulario ICA.
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
        return self.tax_discounts + self.advance_payments + self.withholdings
    
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
    Firma y Responsabilidad - Sección G del formulario ICA.
    Campos para firma digital.
    """
    __tablename__ = "signature_info"
    
    id = Column(Integer, primary_key=True, index=True)
    declaration_id = Column(Integer, ForeignKey("ica_declarations.id"), nullable=False)
    
    # Datos del declarante
    declarant_name = Column(String(255))
    declaration_date = Column(Date)
    
    # Datos del contador / revisor fiscal
    accountant_name = Column(String(255))
    professional_card_number = Column(String(50))
    
    # Firma digital (base64 del canvas)
    signature_image = Column(Text)
    
    # Metadatos de firma
    signed_at = Column(DateTime(timezone=True))
    ip_address = Column(String(50))
    user_agent = Column(String(500))


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
