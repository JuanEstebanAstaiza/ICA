"""
Endpoints para declaraciones ICA.
Basado en: Documents/formulario-ICA.md
"""
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
    DiscountsCredits, DeclarationResult, AuditLog, Municipality
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
from .auth import get_current_active_user, require_role

router = APIRouter(prefix="/declarations", tags=["Declaraciones ICA"])


def generate_form_number(municipality_code: str, year: int) -> str:
    """Genera número único de formulario."""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
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
    """
    # Verificar que el municipio existe
    municipality = db.query(Municipality).filter(
        Municipality.id == data.municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    # Generar número de formulario
    form_number = generate_form_number(municipality.code, data.tax_year)
    
    # Crear declaración
    declaration = ICADeclaration(
        tax_year=data.tax_year,
        declaration_type=DeclarationType(data.declaration_type.value),
        user_id=current_user.id,
        municipality_id=data.municipality_id,
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
    
    # Actualizar Sección D - Liquidación
    if data.settlement:
        settlement = declaration.settlement
        if settlement:
            for key, value in data.settlement.dict(exclude_unset=True).items():
                setattr(settlement, key, value)
            new_values['settlement'] = data.settlement.dict()
    
    # Actualizar Sección E - Descuentos
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
    declaration_content = f"{declaration.id}-{declaration.form_number}-{current_user.id}-{datetime.utcnow().isoformat()}"
    integrity_hash = generate_integrity_hash(declaration_content)
    
    # Actualizar declaración
    declaration.is_signed = True
    declaration.signature_data = signature_data.signature_image
    declaration.signed_at = datetime.utcnow()
    declaration.signed_by_user_id = current_user.id
    declaration.integrity_hash = integrity_hash
    declaration.status = FormStatus.FIRMADO
    
    # Log de auditoría
    audit_log = AuditLog(
        user_id=current_user.id,
        declaration_id=declaration.id,
        action="SIGN",
        entity_type="ICADeclaration",
        entity_id=declaration.id,
        new_values={
            'signed_at': declaration.signed_at.isoformat(),
            'integrity_hash': integrity_hash[:16] + '...'
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    
    db.commit()
    
    return {
        "message": "Declaración firmada correctamente",
        "signed_at": declaration.signed_at,
        "integrity_hash": integrity_hash
    }


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
            'form_title': config.form_title
        }
    
    # Preparar datos para el PDF
    declaration_data = {
        'id': declaration.id,
        'form_number': declaration.form_number,
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
        'result': {}
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
    
    # Sección B - Base Gravable
    if declaration.income_base:
        declaration_data['income_base'] = {
            'row_8_ordinary_income': declaration.income_base.row_8_ordinary_income,
            'row_9_extraordinary_income': declaration.income_base.row_9_extraordinary_income,
            'row_11_returns': declaration.income_base.row_11_returns,
            'row_12_exports': declaration.income_base.row_12_exports,
            'row_13_fixed_assets_sales': declaration.income_base.row_13_fixed_assets_sales,
            'row_14_excluded_income': declaration.income_base.row_14_excluded_income,
            'row_15_non_taxable_income': declaration.income_base.row_15_non_taxable_income
        }
    
    # Sección C - Actividades
    for activity in declaration.activities:
        declaration_data['activities'].append({
            'ciiu_code': activity.ciiu_code,
            'description': activity.description,
            'income': activity.income,
            'tax_rate': activity.tax_rate
        })
    
    # Sección D - Liquidación
    if declaration.settlement:
        declaration_data['settlement'] = {
            'row_30_ica_tax': declaration.settlement.row_30_ica_tax,
            'row_31_signs_boards': declaration.settlement.row_31_signs_boards,
            'row_32_surcharge': declaration.settlement.row_32_surcharge
        }
    
    # Sección E - Descuentos
    if declaration.discounts:
        declaration_data['discounts'] = {
            'tax_discounts': declaration.discounts.tax_discounts,
            'advance_payments': declaration.discounts.advance_payments,
            'withholdings': declaration.discounts.withholdings
        }
    
    # Sección F - Resultado
    if declaration.result:
        declaration_data['result'] = {
            'amount_to_pay': declaration.result.amount_to_pay,
            'balance_in_favor': declaration.result.balance_in_favor
        }
    
    # Generar PDF
    pdf_generator = PDFGenerator(white_label_config)
    pdf_path = pdf_generator.generate_declaration_pdf(declaration_data)
    
    # Actualizar declaración con ruta del PDF
    declaration.pdf_path = pdf_path
    declaration.pdf_generated_at = datetime.utcnow()
    
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
    
    return {
        "message": "PDF generado correctamente",
        "pdf_path": pdf_path,
        "generated_at": declaration.pdf_generated_at
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
