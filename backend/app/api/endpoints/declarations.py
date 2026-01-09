"""
Endpoints para declaraciones ICA.
Basado en: Documents/formulario-ICA.md
"""
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import uuid

from ...db.database import get_db
from ...models.models import (
    User, UserRole, ICADeclaration, DeclarationType, FormStatus,
    Taxpayer, IncomeBase, TaxableActivity, TaxSettlement,
    DiscountsCredits, DeclarationResult, AuditLog, Municipality,
    SignatureInfo
)
from ...schemas.schemas import (
    ICADeclarationCreate, ICADeclarationUpdate, ICADeclarationResponse,
    TaxpayerCreate, IncomeBaseSchema, TaxableActivityBase,
    TaxSettlementBase, DiscountsCreditsBase, SignatureData,
    CalculationRequest, CalculationResponse
)
from ...services.calculation_engine import (
    ICACalculationEngine, IncomeData, ActivityData, SettlementData, CreditsData
)
from ...services.pdf_generator import PDFGenerator
from ...core.security import generate_integrity_hash
from ...core.config import get_colombia_time
from .auth import get_current_active_user, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/declarations", tags=["Declaraciones ICA"])


def generate_form_number(municipality_code: str, year: int) -> str:
    """Genera número único de formulario."""
    timestamp = get_colombia_time().strftime('%Y%m%d%H%M%S')
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"ICA-{municipality_code}-{year}-{timestamp}-{unique_id}"


@router.post("/", response_model=ICADeclarationResponse)
async def create_declaration(
    data: ICADeclarationCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Crea una nueva declaración ICA.
    Sección 1 del formulario: Metadatos Generales.
    Si el usuario tiene un municipio asignado, se usa ese municipio.
    """
    # Determinar el municipio a usar
    # Si el usuario tiene municipio asignado, usar ese (prioritario)
    municipality_id = data.municipality_id
    if current_user.municipality_id:
        municipality_id = current_user.municipality_id
    
    # Verificar que el municipio existe
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    # Generar número de formulario
    form_number = generate_form_number(municipality.code, data.tax_year)
    
    # Crear declaración con el municipio correcto
    declaration = ICADeclaration(
        tax_year=data.tax_year,
        declaration_type=DeclarationType(data.declaration_type.value),
        user_id=current_user.id,
        municipality_id=municipality_id,  # Usar el municipio determinado (del usuario si existe)
        form_number=form_number,
        correction_of_id=data.correction_of_id,
        status=FormStatus.BORRADOR
    )
    
    db.add(declaration)
    db.commit()
    db.refresh(declaration)
    
    # Crear registros relacionados vacíos
    taxpayer = Taxpayer(
        declaration_id=declaration.id,
        document_type="",
        document_number="",
        legal_name=""
    )
    db.add(taxpayer)
    
    income_base = IncomeBase(declaration_id=declaration.id)
    db.add(income_base)
    
    settlement = TaxSettlement(declaration_id=declaration.id)
    db.add(settlement)
    
    discounts = DiscountsCredits(declaration_id=declaration.id)
    db.add(discounts)
    
    result = DeclarationResult(declaration_id=declaration.id)
    db.add(result)
    
    # Log de auditoría
    audit_log = AuditLog(
        user_id=current_user.id,
        declaration_id=declaration.id,
        action="CREATE",
        entity_type="ICADeclaration",
        entity_id=declaration.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(declaration)
    
    return declaration


@router.get("/", response_model=List[ICADeclarationResponse])
async def list_declarations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status_filter: Optional[FormStatus] = None,
    year_filter: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lista las declaraciones del usuario actual.
    Administradores pueden ver todas las de su municipio.
    """
    query = db.query(ICADeclaration)
    
    # Filtrar según rol
    if current_user.role == UserRole.DECLARANTE:
        query = query.filter(ICADeclaration.user_id == current_user.id)
    elif current_user.role == UserRole.ADMIN_ALCALDIA:
        query = query.filter(
            ICADeclaration.municipality_id == current_user.municipality_id
        )
    # ADMIN_SISTEMA puede ver todas
    
    # Aplicar filtros
    if status_filter:
        query = query.filter(ICADeclaration.status == status_filter)
    if year_filter:
        query = query.filter(ICADeclaration.tax_year == year_filter)
    
    declarations = query.order_by(
        ICADeclaration.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return declarations


@router.get("/search", response_model=List[ICADeclarationResponse])
async def search_declarations(
    filing_number: Optional[str] = Query(None, description="Buscar por número de radicado"),
    form_number: Optional[str] = Query(None, description="Buscar por número de formulario"),
    document_number: Optional[str] = Query(None, description="Buscar por documento del contribuyente"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Busca declaraciones por diferentes criterios.
    Para administradores de alcaldía: busca en todas las de su municipio.
    Para declarantes: busca solo en sus propias declaraciones.
    """
    query = db.query(ICADeclaration)
    
    # Filtrar según rol
    if current_user.role == UserRole.DECLARANTE:
        query = query.filter(ICADeclaration.user_id == current_user.id)
    elif current_user.role == UserRole.ADMIN_ALCALDIA:
        query = query.filter(
            ICADeclaration.municipality_id == current_user.municipality_id
        )
    # ADMIN_SISTEMA puede buscar en todas
    
    # Aplicar filtros de búsqueda
    if filing_number:
        query = query.filter(ICADeclaration.filing_number.ilike(f"%{filing_number}%"))
    
    if form_number:
        query = query.filter(ICADeclaration.form_number.ilike(f"%{form_number}%"))
    
    if document_number:
        # Buscar por documento del contribuyente (join con Taxpayer)
        query = query.join(Taxpayer).filter(
            Taxpayer.document_number.ilike(f"%{document_number}%")
        )
    
    # Ordenar por fecha de radicado descendente (más reciente primero)
    declarations = query.order_by(
        ICADeclaration.filing_date.desc().nullslast(),
        ICADeclaration.created_at.desc()
    ).limit(100).all()
    
    return declarations


@router.get("/{declaration_id}", response_model=ICADeclarationResponse)
async def get_declaration(
    declaration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene una declaración específica con todos sus datos.
    """
    declaration = db.query(ICADeclaration).filter(
        ICADeclaration.id == declaration_id
    ).first()
    
    if not declaration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Declaración no encontrada"
        )
    
    # Verificar permisos
    if current_user.role == UserRole.DECLARANTE:
        if declaration.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a esta declaración"
            )
    elif current_user.role == UserRole.ADMIN_ALCALDIA:
        if declaration.municipality_id != current_user.municipality_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a esta declaración"
            )
    
    return declaration


@router.put("/{declaration_id}", response_model=ICADeclarationResponse)
async def update_declaration(
    declaration_id: int,
    data: ICADeclarationUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza una declaración ICA.
    Solo permitido si no está firmada.
    """
    declaration = db.query(ICADeclaration).filter(
        ICADeclaration.id == declaration_id
    ).first()
    
    if not declaration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Declaración no encontrada"
        )
    
    # Verificar que no esté firmada
    if declaration.is_signed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede modificar una declaración firmada"
        )
    
    # Verificar permisos
    if current_user.role == UserRole.DECLARANTE:
        if declaration.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a esta declaración"
            )
    
    old_values = {}
    new_values = {}
    
    # Actualizar Sección A - Contribuyente
    if data.taxpayer:
        taxpayer = declaration.taxpayer
        if taxpayer:
            old_values['taxpayer'] = {
                'document_type': taxpayer.document_type,
                'document_number': taxpayer.document_number,
                'legal_name': taxpayer.legal_name
            }
            for key, value in data.taxpayer.dict(exclude_unset=True).items():
                setattr(taxpayer, key, value)
            new_values['taxpayer'] = data.taxpayer.dict()
    
    # Actualizar Sección B - Base Gravable
    if data.income_base:
        income_base = declaration.income_base
        if income_base:
            old_values['income_base'] = {
                'row_8': income_base.row_8_ordinary_income,
                'row_9': income_base.row_9_extraordinary_income
            }
            for key, value in data.income_base.dict(exclude_unset=True).items():
                setattr(income_base, key, value)
            new_values['income_base'] = data.income_base.dict()
    
    # Actualizar Sección C - Actividades
    if data.activities is not None:
        # Eliminar actividades existentes
        db.query(TaxableActivity).filter(
            TaxableActivity.declaration_id == declaration_id
        ).delete()
        
        # Crear nuevas actividades
        for act_data in data.activities:
            activity = TaxableActivity(
                declaration_id=declaration_id,
                ciiu_code=act_data.ciiu_code,
                description=act_data.description,
                income=act_data.income,
                tax_rate=act_data.tax_rate
            )
            db.add(activity)
        new_values['activities'] = [a.dict() for a in data.activities]
    
    # Actualizar Generación de Energía (Renglones 18-19)
    if data.energy_generation:
        energy = declaration.energy_generation
        if energy:
            for key, value in data.energy_generation.dict(exclude_unset=True).items():
                setattr(energy, key, value)
            new_values['energy_generation'] = data.energy_generation.dict()
    
    # Actualizar Sección D - Liquidación
    if data.settlement:
        settlement = declaration.settlement
        if settlement:
            for key, value in data.settlement.dict(exclude_unset=True).items():
                setattr(settlement, key, value)
            new_values['settlement'] = data.settlement.dict()
    
    # Actualizar Sección E - Pago
    if data.payment_section:
        payment = declaration.payment_section
        if payment:
            for key, value in data.payment_section.dict(exclude_unset=True).items():
                setattr(payment, key, value)
            new_values['payment_section'] = data.payment_section.dict()
    
    # Actualizar Sección E - Descuentos (legacy)
    if data.discounts:
        discounts = declaration.discounts
        if discounts:
            for key, value in data.discounts.dict(exclude_unset=True).items():
                setattr(discounts, key, value)
            new_values['discounts'] = data.discounts.dict()
    
    # Log de auditoría
    audit_log = AuditLog(
        user_id=current_user.id,
        declaration_id=declaration.id,
        action="UPDATE",
        entity_type="ICADeclaration",
        entity_id=declaration.id,
        old_values=old_values,
        new_values=new_values,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(declaration)
    
    return declaration


@router.post("/{declaration_id}/calculate", response_model=CalculationResponse)
async def calculate_declaration(
    declaration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Calcula automáticamente todos los valores del formulario.
    Usa el motor de reglas desacoplado.
    """
    declaration = db.query(ICADeclaration).filter(
        ICADeclaration.id == declaration_id
    ).first()
    
    if not declaration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Declaración no encontrada"
        )
    
    # Preparar datos para el motor de cálculo
    income_data = IncomeData(
        row_8_ordinary_income=declaration.income_base.row_8_ordinary_income if declaration.income_base else 0,
        row_9_extraordinary_income=declaration.income_base.row_9_extraordinary_income if declaration.income_base else 0,
        row_11_returns=declaration.income_base.row_11_returns if declaration.income_base else 0,
        row_12_exports=declaration.income_base.row_12_exports if declaration.income_base else 0,
        row_13_fixed_assets_sales=declaration.income_base.row_13_fixed_assets_sales if declaration.income_base else 0,
        row_14_excluded_income=declaration.income_base.row_14_excluded_income if declaration.income_base else 0,
        row_15_non_taxable_income=declaration.income_base.row_15_non_taxable_income if declaration.income_base else 0,
    )
    
    activities = [
        ActivityData(
            ciiu_code=act.ciiu_code,
            income=act.income,
            tax_rate=act.tax_rate
        )
        for act in declaration.activities
    ]
    
    settlement_data = SettlementData(
        row_31_signs_boards=declaration.settlement.row_31_signs_boards if declaration.settlement else 0,
        row_32_surcharge=declaration.settlement.row_32_surcharge if declaration.settlement else 0,
    )
    
    credits_data = CreditsData(
        tax_discounts=declaration.discounts.tax_discounts if declaration.discounts else 0,
        advance_payments=declaration.discounts.advance_payments if declaration.discounts else 0,
        withholdings=declaration.discounts.withholdings if declaration.discounts else 0,
    )
    
    # Ejecutar cálculo
    result = ICACalculationEngine.calculate_full_declaration(
        income_data, activities, settlement_data, credits_data
    )
    
    # Actualizar valores calculados en la declaración
    if declaration.settlement:
        declaration.settlement.row_30_ica_tax = result.row_30_ica_tax
    
    if declaration.result:
        declaration.result.amount_to_pay = result.amount_to_pay
        declaration.result.balance_in_favor = result.balance_in_favor
    
    db.commit()
    
    return CalculationResponse(
        row_10_total_income=result.row_10_total_income,
        row_16_taxable_income=result.row_16_taxable_income,
        total_activities_tax=result.total_activities_tax,
        row_33_total_tax=result.row_33_total_tax,
        total_credits=result.total_credits,
        amount_to_pay=result.amount_to_pay,
        balance_in_favor=result.balance_in_favor
    )


@router.post("/{declaration_id}/sign")
async def sign_declaration(
    declaration_id: int,
    signature_data: SignatureData,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Firma digital de la declaración.
    Una vez firmado, el formulario queda bloqueado.
    Genera el número de radicado automáticamente.
    """
    declaration = db.query(ICADeclaration).filter(
        ICADeclaration.id == declaration_id
    ).first()
    
    if not declaration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Declaración no encontrada"
        )
    
    if declaration.is_signed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La declaración ya está firmada"
        )
    
    # Verificar permisos
    if declaration.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el propietario puede firmar la declaración"
        )
    
    # Generar hash de integridad
    colombia_now = get_colombia_time()
    declaration_content = f"{declaration.id}-{declaration.form_number}-{current_user.id}-{colombia_now.isoformat()}"
    integrity_hash = generate_integrity_hash(declaration_content)
    
    # Generar número de radicado usando configuración del municipio
    filing_number = None
    municipality = declaration.municipality
    if municipality and municipality.config:
        config = municipality.config
        prefijo = config.radicado_prefijo or ""
        numero = config.radicado_actual or 1
        digitos = config.radicado_digitos or 16
        
        # Formato: PREFIJO + número con ceros a la izquierda
        filing_number = f"{prefijo}{str(numero).zfill(digitos)}"
        
        # Incrementar el contador para el próximo radicado
        config.radicado_actual = numero + 1
    else:
        # Si no hay configuración, generar uno genérico
        filing_number = f"RAD-{declaration.id}-{colombia_now.strftime('%Y%m%d%H%M%S')}"
    
    # Actualizar declaración
    declaration.is_signed = True
    declaration.signature_data = signature_data.signature_image
    declaration.signed_at = colombia_now
    declaration.filing_date = colombia_now  # Fecha de presentación
    declaration.filing_number = filing_number  # Número de radicado
    declaration.signed_by_user_id = current_user.id
    declaration.integrity_hash = integrity_hash
    declaration.status = FormStatus.FIRMADO
    
    # Crear o actualizar SignatureInfo con todos los datos del firmante
    # Eliminar firma anterior si existe
    if declaration.signature_info:
        db.delete(declaration.signature_info)
        db.flush()  # Ensure the deletion is processed before adding new record
    
    # Crear nueva información de firma
    signature_info = SignatureInfo(
        declaration_id=declaration.id,
        declarant_name=signature_data.declarant_name,
        declarant_document=signature_data.declarant_document,
        declarant_signature_method=signature_data.declarant_signature_method,
        declarant_signature_image=signature_data.signature_image,
        declarant_oath_accepted=signature_data.declarant_oath_accepted,
        declaration_date=signature_data.declaration_date,
        requires_fiscal_reviewer=signature_data.requires_fiscal_reviewer,
        accountant_name=signature_data.accountant_name,
        accountant_document=signature_data.accountant_document,
        accountant_professional_card=signature_data.accountant_professional_card,
        accountant_signature_method=signature_data.accountant_signature_method,
        accountant_signature_image=signature_data.accountant_signature_image,
        document_hash=integrity_hash,
        signed_at=colombia_now,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        integrity_verified=True
    )
    db.add(signature_info)
    
    # Log de auditoría
    audit_log = AuditLog(
        user_id=current_user.id,
        declaration_id=declaration.id,
        action="SIGN",
        entity_type="ICADeclaration",
        entity_id=declaration.id,
        new_values={
            'signed_at': declaration.signed_at.isoformat(),
            'filing_number': filing_number,
            'integrity_hash': integrity_hash[:16] + '...',
            'declarant_name': signature_data.declarant_name
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error al firmar declaración {declaration_id}: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar la firma"
        )
    
    return {
        "message": "Declaración firmada correctamente",
        "signed_at": declaration.signed_at,
        "filing_number": filing_number,
        "integrity_hash": integrity_hash
    }


@router.post("/{declaration_id}/correct", response_model=ICADeclarationResponse)
async def create_correction_declaration(
    declaration_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Crea una corrección de una declaración firmada.
    - Solo el propietario puede corregir su declaración
    - La declaración original debe estar firmada
    - Solo se permite 1 corrección por declaración original
    - Los datos se copian pero el formulario queda en estado borrador
    - Se genera un nuevo número de radicado al firmar la corrección
    """
    # Obtener declaración original
    original = db.query(ICADeclaration).filter(
        ICADeclaration.id == declaration_id
    ).first()
    
    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Declaración no encontrada"
        )
    
    # Verificar que sea el propietario
    if original.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el propietario puede corregir la declaración"
        )
    
    # Verificar que esté firmada
    if not original.is_signed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden corregir declaraciones firmadas"
        )
    
    # Verificar que no haya sido corregida anteriormente
    if original.has_been_corrected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta declaración ya ha sido corregida. Solo se permite 1 corrección por formulario."
        )
    
    # Verificar que la declaración original no sea ya una corrección que haya sido corregida
    # (No se permite corregir una corrección)
    if original.correction_of_id:
        # Es una corrección, verificar que no pueda corregirse de nuevo
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede corregir una declaración que ya es una corrección. Debe crear un nuevo formulario."
        )
    
    # Generar número de formulario para la corrección
    municipality = original.municipality
    form_number = generate_form_number(municipality.code, original.tax_year)
    
    # Crear nueva declaración como corrección
    correction = ICADeclaration(
        tax_year=original.tax_year,
        declaration_type=DeclarationType.CORRECCION,
        user_id=current_user.id,
        municipality_id=original.municipality_id,
        form_number=form_number,
        correction_of_id=original.id,  # Referencia al original
        status=FormStatus.BORRADOR,
        is_signed=False
    )
    
    db.add(correction)
    db.flush()  # Para obtener el ID
    
    # Copiar Taxpayer
    if original.taxpayer:
        t = original.taxpayer
        new_taxpayer = Taxpayer(
            declaration_id=correction.id,
            document_type=t.document_type,
            document_number=t.document_number,
            verification_digit=t.verification_digit,
            legal_name=t.legal_name,
            entity_type=t.entity_type,
            address=t.address,
            notification_department=t.notification_department,
            notification_municipality=t.notification_municipality,
            municipality=t.municipality,
            department=t.department,
            phone=t.phone,
            email=t.email,
            num_establishments=t.num_establishments,
            taxpayer_classification=t.taxpayer_classification
        )
        db.add(new_taxpayer)
    
    # Copiar IncomeBase (todos los campos de la Sección B)
    if original.income_base:
        ib = original.income_base
        new_income = IncomeBase(
            declaration_id=correction.id,
            # Campos principales
            row_8_total_income_country=ib.row_8_total_income_country,
            row_9_income_outside_municipality=ib.row_9_income_outside_municipality,
            row_11_returns_rebates_discounts=ib.row_11_returns_rebates_discounts,
            row_12_exports_fixed_assets=ib.row_12_exports_fixed_assets,
            row_13_excluded_non_taxable=ib.row_13_excluded_non_taxable,
            row_14_exempt_income=ib.row_14_exempt_income,
            # Campos adicionales del desglose
            row_8_ordinary_income=ib.row_8_ordinary_income,
            row_9_extraordinary_income=ib.row_9_extraordinary_income,
            row_11_returns=ib.row_11_returns,
            row_12_exports=ib.row_12_exports,
            row_13_fixed_assets_sales=ib.row_13_fixed_assets_sales,
            row_14_excluded_income=ib.row_14_excluded_income,
            row_15_non_taxable_income=ib.row_15_non_taxable_income
        )
        db.add(new_income)
    
    # Copiar actividades
    for act in original.activities:
        new_act = TaxableActivity(
            declaration_id=correction.id,
            activity_type=act.activity_type,
            ciiu_code=act.ciiu_code,
            description=act.description,
            income=act.income,
            tax_rate=act.tax_rate,
            special_rate=act.special_rate
        )
        db.add(new_act)
    
    # Copiar TaxSettlement (todos los campos de la Sección D)
    if original.settlement:
        s = original.settlement
        new_settlement = TaxSettlement(
            declaration_id=correction.id,
            # Campos principales de liquidación
            row_20_total_ica_tax=s.row_20_total_ica_tax,
            row_21_signs_boards=s.row_21_signs_boards,
            row_22_financial_additional_units=s.row_22_financial_additional_units,
            row_23_bomberil_surcharge=s.row_23_bomberil_surcharge,
            row_24_security_surcharge=s.row_24_security_surcharge,
            row_26_exemptions=s.row_26_exemptions,
            row_27_withholdings_municipality=s.row_27_withholdings_municipality,
            row_28_self_withholdings=s.row_28_self_withholdings,
            row_29_previous_advance=s.row_29_previous_advance,
            row_30_next_year_advance=s.row_30_next_year_advance,
            row_31_penalties=s.row_31_penalties,
            row_31_penalty_type=s.row_31_penalty_type,
            row_31_penalty_other_description=s.row_31_penalty_other_description,
            row_32_previous_balance_favor=s.row_32_previous_balance_favor,
            # Campos adicionales
            row_30_ica_tax=s.row_30_ica_tax,
            row_31_signs_boards=s.row_31_signs_boards,
            row_32_surcharge=s.row_32_surcharge
        )
        db.add(new_settlement)
    
    # Copiar DiscountsCredits
    if original.discounts:
        d = original.discounts
        new_discounts = DiscountsCredits(
            declaration_id=correction.id,
            tax_discounts=d.tax_discounts,
            advance_payments=d.advance_payments,
            withholdings=d.withholdings
        )
        db.add(new_discounts)
    
    # Copiar resultado
    if original.result:
        r = original.result
        new_result = DeclarationResult(
            declaration_id=correction.id,
            amount_to_pay=r.amount_to_pay,
            balance_in_favor=r.balance_in_favor
        )
        db.add(new_result)
    
    # Marcar la declaración original como corregida
    original.has_been_corrected = True
    
    # Log de auditoría
    audit_log = AuditLog(
        user_id=current_user.id,
        declaration_id=original.id,
        action="CORRECTION_CREATED",
        entity_type="ICADeclaration",
        entity_id=correction.id,
        new_values={
            'correction_id': correction.id,
            'original_id': original.id,
            'form_number': form_number
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(correction)
    
    return correction


@router.post("/{declaration_id}/generate-pdf")
async def generate_pdf(
    declaration_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Genera el PDF de la declaración.
    El PDF se guarda en el filesystem local del servidor.
    """
    declaration = db.query(ICADeclaration).filter(
        ICADeclaration.id == declaration_id
    ).first()
    
    if not declaration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Declaración no encontrada"
        )
    
    # Obtener configuración marca blanca
    municipality = declaration.municipality
    white_label_config = {}
    if municipality and municipality.config:
        config = municipality.config
        white_label_config = {
            'logo_path': config.logo_path,
            'primary_color': config.primary_color,
            'secondary_color': config.secondary_color,
            'font_family': config.font_family,
            'header_text': config.header_text,
            'footer_text': config.footer_text,
            'legal_notes': config.legal_notes,
            'form_title': config.form_title,
            'watermark_text': config.watermark_text  # Marca de agua
        }
    
    # Preparar datos para el PDF
    declaration_data = {
        'id': declaration.id,
        'form_number': declaration.form_number,
        'filing_number': declaration.filing_number,  # Número de radicado
        'filing_date': declaration.filing_date.isoformat() if declaration.filing_date else None,
        'tax_year': declaration.tax_year,
        'declaration_type': declaration.declaration_type.value,
        'status': declaration.status.value,
        'user_id': declaration.user_id,
        'municipality': {
            'name': municipality.name if municipality else '',
            'department': municipality.department if municipality else '',
            'code': municipality.code if municipality else ''
        },
        'is_signed': declaration.is_signed,
        'signed_at': declaration.signed_at.isoformat() if declaration.signed_at else None,
        'integrity_hash': declaration.integrity_hash,
        'signature_data': declaration.signature_data,
        'taxpayer': {},
        'income_base': {},
        'activities': [],
        'settlement': {},
        'discounts': {},
        'result': {},
        'signature_info': {}
    }
    
    # Información de firma del declarante
    if declaration.signature_info:
        sig = declaration.signature_info
        declaration_data['signature_info'] = {
            'declarant_name': sig.declarant_name,
            'declarant_document': sig.declarant_document,
            'declarant_signature_method': sig.declarant_signature_method,
            'declarant_signature_image': sig.declarant_signature_image,
            'declarant_oath_accepted': sig.declarant_oath_accepted,
            'declaration_date': sig.declaration_date.isoformat() if sig.declaration_date else None,
            'requires_fiscal_reviewer': sig.requires_fiscal_reviewer,
            'accountant_name': sig.accountant_name,
            'accountant_document': sig.accountant_document,
            'accountant_professional_card': sig.accountant_professional_card,
            'accountant_signature_method': sig.accountant_signature_method,
            'accountant_signature_image': sig.accountant_signature_image,
            'signed_at': sig.signed_at.isoformat() if sig.signed_at else None
        }
    
    # Sección A - Contribuyente
    if declaration.taxpayer:
        declaration_data['taxpayer'] = {
            'document_type': declaration.taxpayer.document_type,
            'document_number': declaration.taxpayer.document_number,
            'verification_digit': declaration.taxpayer.verification_digit,
            'legal_name': declaration.taxpayer.legal_name,
            'address': declaration.taxpayer.address,
            'municipality': declaration.taxpayer.municipality,
            'department': declaration.taxpayer.department,
            'phone': declaration.taxpayer.phone,
            'email': declaration.taxpayer.email
        }
    
    # Sección B - Base Gravable (Renglones 8-15)
    if declaration.income_base:
        ib = declaration.income_base
        # Cálculos
        row_10 = (ib.row_8_total_income_country or 0) - (ib.row_9_income_outside_municipality or 0)
        row_15 = row_10 - (
            (ib.row_11_returns_rebates_discounts or 0) + 
            (ib.row_12_exports_fixed_assets or 0) + 
            (ib.row_13_excluded_non_taxable or 0) + 
            (ib.row_14_exempt_income or 0)
        )
        declaration_data['income_base'] = {
            'row_8': ib.row_8_total_income_country or 0,
            'row_9': ib.row_9_income_outside_municipality or 0,
            'row_10': row_10,
            'row_11': ib.row_11_returns_rebates_discounts or 0,
            'row_12': ib.row_12_exports_fixed_assets or 0,
            'row_13': ib.row_13_excluded_non_taxable or 0,
            'row_14': ib.row_14_exempt_income or 0,
            'row_15': row_15
        }
    
    # Sección C - Actividades
    total_activities_income = 0
    total_activities_tax = 0
    for activity in declaration.activities:
        income = activity.income or 0
        rate = activity.tax_rate or 0
        tax = income * rate / 100  # Porcentaje
        total_activities_income += income
        total_activities_tax += tax
        declaration_data['activities'].append({
            'ciiu_code': activity.ciiu_code,
            'description': activity.description,
            'income': income,
            'tax_rate': rate,
            'generated_tax': tax
        })
    
    # Renglones 16-17: Totales de actividades
    declaration_data['activities_totals'] = {
        'row_16': total_activities_income,
        'row_17': total_activities_tax
    }
    
    # Energía - Ley 56 (Renglones 18-19)
    if declaration.energy_generation:
        eg = declaration.energy_generation
        declaration_data['energy'] = {
            'row_18': eg.installed_capacity_kw or 0,
            'row_19': eg.law_56_tax or 0
        }
    else:
        declaration_data['energy'] = {'row_18': 0, 'row_19': 0}
    
    # Sección D - Liquidación (Renglones 20-34)
    if declaration.settlement:
        s = declaration.settlement
        # Cálculos
        row_20 = total_activities_tax + (declaration_data['energy']['row_19'] or 0)
        row_25 = row_20 + (s.row_21_signs_boards or 0) + (s.row_22_financial_additional_units or 0) + (s.row_23_bomberil_surcharge or 0) + (s.row_24_security_surcharge or 0)
        balance = row_25 - (s.row_26_exemptions or 0) - (s.row_27_withholdings_municipality or 0) - (s.row_28_self_withholdings or 0) - (s.row_29_previous_advance or 0) + (s.row_30_next_year_advance or 0) + (s.row_31_penalties or 0) - (s.row_32_previous_balance_favor or 0)
        row_33 = balance if balance > 0 else 0
        row_34 = abs(balance) if balance < 0 else 0
        
        declaration_data['settlement'] = {
            'row_20': row_20,
            'row_21': s.row_21_signs_boards or 0,
            'row_22': s.row_22_financial_additional_units or 0,
            'row_23': s.row_23_bomberil_surcharge or 0,
            'row_24': s.row_24_security_surcharge or 0,
            'row_25': row_25,
            'row_26': s.row_26_exemptions or 0,
            'row_27': s.row_27_withholdings_municipality or 0,
            'row_28': s.row_28_self_withholdings or 0,
            'row_29': s.row_29_previous_advance or 0,
            'row_30': s.row_30_next_year_advance or 0,
            'row_31': s.row_31_penalties or 0,
            'row_32': s.row_32_previous_balance_favor or 0,
            'row_33': row_33,
            'row_34': row_34
        }
    else:
        # Valores por defecto si no hay settlement
        declaration_data['settlement'] = {
            'row_20': total_activities_tax,
            'row_21': 0, 'row_22': 0, 'row_23': 0, 'row_24': 0,
            'row_25': total_activities_tax,
            'row_26': 0, 'row_27': 0, 'row_28': 0, 'row_29': 0,
            'row_30': 0, 'row_31': 0, 'row_32': 0,
            'row_33': total_activities_tax, 'row_34': 0
        }
    
    # Sección E - Pago (Renglones 35-40)
    if declaration.payment_section:
        p = declaration.payment_section
        row_35 = declaration_data['settlement']['row_33']  # Saldo a cargo
        row_38 = (row_35 or 0) - (p.row_36_early_payment_discount or 0) + (p.row_37_late_interest or 0)
        row_40 = row_38 + (p.row_39_voluntary_payment or 0)
        
        declaration_data['payment'] = {
            'row_35': row_35,
            'row_36': p.row_36_early_payment_discount or 0,
            'row_37': p.row_37_late_interest or 0,
            'row_38': row_38,
            'row_39': p.row_39_voluntary_payment or 0,
            'row_39_destination': p.row_39_voluntary_destination or '',
            'row_40': row_40
        }
    else:
        row_35 = declaration_data['settlement']['row_33']
        declaration_data['payment'] = {
            'row_35': row_35, 'row_36': 0, 'row_37': 0,
            'row_38': row_35, 'row_39': 0, 'row_39_destination': '',
            'row_40': row_35
        }
    
    # Resultado final (resumen)
    declaration_data['result'] = {
        'amount_to_pay': declaration_data['settlement']['row_33'],
        'balance_in_favor': declaration_data['settlement']['row_34']
    }
    
    # Generar PDF
    pdf_generator = PDFGenerator(white_label_config)
    pdf_path = pdf_generator.generate_declaration_pdf(declaration_data)
    
    # Actualizar declaración con ruta del PDF
    declaration.pdf_path = pdf_path
    declaration.pdf_generated_at = get_colombia_time()
    
    # Log de auditoría
    audit_log = AuditLog(
        user_id=current_user.id,
        declaration_id=declaration.id,
        action="GENERATE_PDF",
        entity_type="ICADeclaration",
        entity_id=declaration.id,
        new_values={'pdf_path': pdf_path},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    
    db.commit()
    
    # Enviar PDF por correo electrónico si está firmado
    email_sent = False
    if declaration.is_signed and declaration.taxpayer and declaration.taxpayer.email:
        try:
            from ...services.email_service import email_service
            email_sent = email_service.send_signed_form_email(
                to_email=declaration.taxpayer.email,
                full_name=declaration.taxpayer.legal_name or "Contribuyente",
                form_number=declaration.form_number or "",
                filing_number=declaration.filing_number or "",
                tax_year=declaration.tax_year,
                amount_to_pay=declaration_data['result'].get('amount_to_pay', 0),
                pdf_path=pdf_path,
                municipality_name=municipality.name if municipality else None
            )
        except Exception as e:
            logger.warning(f"Error sending signed form email: {e}")
    
    return {
        "message": "PDF generado correctamente",
        "pdf_path": pdf_path,
        "generated_at": declaration.pdf_generated_at,
        "email_sent": email_sent
    }


@router.get("/{declaration_id}/download-pdf")
async def download_pdf(
    declaration_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Descarga el PDF de la declaración.
    """
    declaration = db.query(ICADeclaration).filter(
        ICADeclaration.id == declaration_id
    ).first()
    
    if not declaration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Declaración no encontrada"
        )
    
    if not declaration.pdf_path or not os.path.exists(declaration.pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF no encontrado. Genere el PDF primero."
        )
    
    # Verificar permisos
    if current_user.role == UserRole.DECLARANTE:
        if declaration.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a esta declaración"
            )
    
    # Log de auditoría
    audit_log = AuditLog(
        user_id=current_user.id,
        declaration_id=declaration.id,
        action="DOWNLOAD",
        entity_type="ICADeclaration",
        entity_id=declaration.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    db.commit()
    
    filename = os.path.basename(declaration.pdf_path)
    return FileResponse(
        declaration.pdf_path,
        filename=filename,
        media_type="application/pdf"
    )
