"""
Endpoints para administración de alcaldías y configuración marca blanca.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import os
import uuid

from ...db.database import get_db
from ...models.models import (
    User, UserRole, Municipality, WhiteLabelConfig, TaxActivity, FormulaParameters,
    ICADeclaration, AuditLog
)
from ...schemas.schemas import (
    MunicipalityCreate, MunicipalityResponse,
    WhiteLabelConfigUpdate, WhiteLabelConfigResponse,
    TaxActivityCreate, TaxActivityResponse,
    FormulaParametersCreate, FormulaParametersUpdate, FormulaParametersResponse,
    AdminUserCreate, UserStatusUpdate
)
from ...core.config import settings
from ...core.security import get_password_hash
from .auth import get_current_active_user, require_role

# Import CIIU codes from national catalog
try:
    from scripts.ciiu_codes_data import CIIU_CODES
except ImportError:
    CIIU_CODES = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Administración"])


# ===================== MUNICIPIOS =====================

@router.post("/municipalities", response_model=MunicipalityResponse)
async def create_municipality(
    data: MunicipalityCreate,
    current_user: User = Depends(require_role([UserRole.ADMIN_SISTEMA])),
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo municipio.
    Solo administradores del sistema.
    """
    existing = db.query(Municipality).filter(
        Municipality.code == data.code
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un municipio con ese código"
        )
    
    municipality = Municipality(
        code=data.code,
        name=data.name,
        department=data.department
    )
    
    db.add(municipality)
    db.commit()
    db.refresh(municipality)
    
    # Crear configuración marca blanca por defecto
    config = WhiteLabelConfig()
    db.add(config)
    db.commit()
    
    municipality.config_id = config.id
    db.commit()
    
    return municipality


@router.get("/municipalities", response_model=List[MunicipalityResponse])
async def list_municipalities(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lista todos los municipios.
    """
    municipalities = db.query(Municipality).filter(
        Municipality.is_active == True
    ).all()
    
    return municipalities


@router.get("/municipalities/{municipality_id}", response_model=MunicipalityResponse)
async def get_municipality(
    municipality_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene un municipio específico.
    """
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    return municipality


@router.put("/municipalities/{municipality_id}", response_model=MunicipalityResponse)
async def update_municipality(
    municipality_id: int,
    data: MunicipalityCreate,
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Actualiza datos de un municipio (código DANE, nombre, departamento).
    Permite correcciones en caliente si el código DANE es incorrecto.
    """
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    # Verificar que el nuevo código no exista en otro municipio
    if data.code != municipality.code:
        existing = db.query(Municipality).filter(
            Municipality.code == data.code,
            Municipality.id != municipality_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El código DANE {data.code} ya está asignado a otro municipio"
            )
    
    municipality.code = data.code
    municipality.name = data.name
    municipality.department = data.department
    
    db.commit()
    db.refresh(municipality)
    
    return municipality


# ===================== CONFIGURACIÓN MARCA BLANCA =====================

@router.get("/white-label/{municipality_id}", response_model=WhiteLabelConfigResponse)
async def get_white_label_config(
    municipality_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene la configuración marca blanca de un municipio.
    Si no existe, crea una configuración por defecto.
    """
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    # Si no tiene configuración, crearla automáticamente
    if not municipality.config:
        try:
            config = WhiteLabelConfig()
            db.add(config)
            db.flush()  # Flush to get the config.id
            municipality.config_id = config.id
            db.commit()
            db.refresh(config)
            # Early return: Return the config object directly to avoid SQLAlchemy
            # relationship caching issues where municipality.config might still be None
            # after setting config_id and committing
            return config
        except (SQLAlchemyError, IntegrityError) as e:
            db.rollback()
            logger.error(f"Error al crear configuración marca blanca para municipio {municipality_id}: {type(e).__name__}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear la configuración"
            )
    
    return municipality.config


@router.put("/white-label/{municipality_id}", response_model=WhiteLabelConfigResponse)
async def update_white_label_config(
    municipality_id: int,
    data: WhiteLabelConfigUpdate,
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Actualiza la configuración marca blanca.
    Permite personalizar:
    - Textos del formulario
    - Encabezados y notas legales
    - Colores
    - Tipografías
    """
    # Verificar permisos para admin de alcaldía
    if current_user.role == UserRole.ADMIN_ALCALDIA:
        if current_user.municipality_id != municipality_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede modificar la configuración de su municipio"
            )
    
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    config = municipality.config
    if not config:
        try:
            config = WhiteLabelConfig()
            db.add(config)
            db.flush()  # Flush to get the config.id
            municipality.config_id = config.id
            db.commit()
            db.refresh(config)
        except (SQLAlchemyError, IntegrityError) as e:
            db.rollback()
            logger.error(f"Error al crear configuración marca blanca para municipio {municipality_id}: {type(e).__name__}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear la configuración"
            )
    
    # Actualizar campos
    for key, value in data.dict(exclude_unset=True).items():
        setattr(config, key, value)
    
    config.updated_by = current_user.id
    
    try:
        db.commit()
        db.refresh(config)
    except (SQLAlchemyError, IntegrityError) as e:
        db.rollback()
        logger.error(f"Error al actualizar configuración marca blanca para municipio {municipality_id}: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar la configuración"
        )
    
    return config


@router.post("/white-label/{municipality_id}/logo")
async def upload_logo(
    municipality_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Sube el logo institucional del municipio.
    """
    # Verificar permisos
    if current_user.role == UserRole.ADMIN_ALCALDIA:
        if current_user.municipality_id != municipality_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede modificar la configuración de su municipio"
            )
    
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    # Validar tipo de archivo
    allowed_types = ['image/png', 'image/jpeg', 'image/jpg']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de archivo no permitido. Use PNG o JPEG."
        )
    
    # Guardar archivo
    assets_path = os.path.join(settings.ASSETS_STORAGE_PATH, str(municipality_id))
    os.makedirs(assets_path, exist_ok=True)
    
    file_extension = file.filename.split('.')[-1] if file.filename else 'png'
    filename = f"logo_{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(assets_path, filename)
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Actualizar configuración
    config = municipality.config
    if config:
        config.logo_path = file_path
        config.updated_by = current_user.id
        db.commit()
    
    return {"message": "Logo subido correctamente", "path": file_path}


# ===================== ACTIVIDADES ECONÓMICAS (CÓDIGOS CIIU) =====================
# Los códigos CIIU vienen precargados del catálogo nacional (504 códigos de 4 dígitos).
# Organizados por secciones (A-U) según la clasificación oficial.
# Solo la tarifa (tax_rate) es editable por el administrador.

@router.get("/activities/{municipality_id}", response_model=List[TaxActivityResponse])
async def list_tax_activities(
    municipality_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lista las actividades económicas de un municipio.
    """
    activities = db.query(TaxActivity).filter(
        TaxActivity.municipality_id == municipality_id,
        TaxActivity.is_active == True
    ).all()
    
    return activities


@router.get("/activities/{municipality_id}/sections")
async def list_ciiu_sections(
    municipality_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lista las secciones CIIU disponibles para un municipio.
    Usado para el filtro por sección en el panel de admin y formulario del declarante.
    
    Returns:
        Lista de secciones con código y nombre
    """
    # Obtener secciones únicas de las actividades del municipio
    sections = db.query(
        TaxActivity.section_code,
        TaxActivity.section_name
    ).filter(
        TaxActivity.municipality_id == municipality_id,
        TaxActivity.is_active == True,
        TaxActivity.section_code.isnot(None)
    ).distinct().order_by(TaxActivity.section_code).all()
    
    return [
        {
            "section_code": s.section_code,
            "section_name": s.section_name,
        }
        for s in sections
    ]


@router.get("/activities/{municipality_id}/paginated")
async def list_tax_activities_paginated(
    municipality_id: int,
    page: int = 1,
    per_page: int = 10,
    search: Optional[str] = None,
    section: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lista las actividades económicas de un municipio con paginación.
    Útil para el panel de administración cuando hay muchos códigos CIIU.
    
    Args:
        municipality_id: ID del municipio
        page: Número de página (default 1)
        per_page: Elementos por página (default 10, max 100)
        search: Término de búsqueda para filtrar por código CIIU o descripción
        section: Código de sección para filtrar (ej: 'SECCIÓN A')
    """
    # Validar parámetros
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 10
    if per_page > 100:
        per_page = 100
    
    # Construir query base
    query = db.query(TaxActivity).filter(
        TaxActivity.municipality_id == municipality_id,
        TaxActivity.is_active == True
    )
    
    # Aplicar filtro de sección si existe
    if section:
        query = query.filter(TaxActivity.section_code == section)
    
    # Aplicar filtro de búsqueda si existe
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (TaxActivity.ciiu_code.ilike(search_term)) |
            (TaxActivity.description.ilike(search_term))
        )
    
    # Obtener total
    total = query.count()
    
    # Aplicar paginación
    offset = (page - 1) * per_page
    activities = query.order_by(TaxActivity.section_code, TaxActivity.ciiu_code).offset(offset).limit(per_page).all()
    
    # Calcular páginas
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    return {
        "items": [
            {
                "id": a.id,
                "municipality_id": a.municipality_id,
                "ciiu_code": a.ciiu_code,
                "description": a.description,
                "tax_rate": a.tax_rate,
                "section_code": a.section_code,
                "section_name": a.section_name,
                "is_active": a.is_active
            }
            for a in activities
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }


@router.get("/activities/{municipality_id}/search")
async def search_tax_activities(
    municipality_id: int,
    q: str,
    limit: int = 10,
    section: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Busca actividades económicas por código CIIU o descripción.
    Usado para autocompletado en el formulario del declarante.
    
    Args:
        municipality_id: ID del municipio
        q: Término de búsqueda
        limit: Máximo de resultados (default 10)
        section: Filtrar por sección (ej: 'SECCIÓN A')
    """
    if not q or len(q) < 1:
        return []
    
    if limit > 50:
        limit = 50
    
    search_term = f"%{q}%"
    
    query = db.query(TaxActivity).filter(
        TaxActivity.municipality_id == municipality_id,
        TaxActivity.is_active == True,
        (TaxActivity.ciiu_code.ilike(search_term)) |
        (TaxActivity.description.ilike(search_term))
    )
    
    # Aplicar filtro de sección si se proporciona
    if section:
        query = query.filter(TaxActivity.section_code == section)
    
    activities = query.order_by(TaxActivity.section_code, TaxActivity.ciiu_code).limit(limit).all()
    
    return [
        {
            "id": a.id,
            "ciiu_code": a.ciiu_code,
            "description": a.description,
            "tax_rate": a.tax_rate,
            "section_code": a.section_code,
            "section_name": a.section_name
        }
        for a in activities
    ]


@router.post("/activities/{municipality_id}/seed")
async def seed_ciiu_codes(
    municipality_id: int,
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Carga los 504 códigos CIIU del catálogo nacional para un municipio.
    Los códigos se crean con tarifa inicial 0% - el administrador debe configurar las tarifas.
    
    Este endpoint reemplaza la carga masiva por CSV.
    Los códigos CIIU y descripciones son fijos del catálogo nacional.
    Solo la tarifa (tax_rate) es editable posteriormente.
    """
    # Default tax rate for new CIIU codes - admin must configure actual rates
    DEFAULT_TAX_RATE = 0.0
    
    # Verificar que el catálogo de códigos CIIU está disponible
    if CIIU_CODES is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo cargar el catálogo de códigos CIIU"
        )
    
    # Verificar permisos
    if current_user.role == UserRole.ADMIN_ALCALDIA:
        if current_user.municipality_id != municipality_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede cargar códigos para su municipio"
            )
    
    # Verificar que el municipio existe
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    created_count = 0
    updated_count = 0
    existing_count = 0
    
    for ciiu in CIIU_CODES:
        # Verificar si ya existe
        existing = db.query(TaxActivity).filter(
            TaxActivity.municipality_id == municipality_id,
            TaxActivity.ciiu_code == ciiu['ciiu_code']
        ).first()
        
        if existing:
            # Si existe pero le falta la sección, actualizarla
            if not existing.section_code or not existing.section_name:
                existing.section_code = ciiu['section_code']
                existing.section_name = ciiu['section_name']
                updated_count += 1
            existing_count += 1
        else:
            # Crear nueva actividad con tarifa inicial (el admin debe configurarla)
            activity = TaxActivity(
                municipality_id=municipality_id,
                ciiu_code=ciiu['ciiu_code'],
                description=ciiu['description'],
                tax_rate=DEFAULT_TAX_RATE,
                section_code=ciiu['section_code'],
                section_name=ciiu['section_name'],
                is_active=True
            )
            db.add(activity)
            created_count += 1
    
    db.commit()
    
    return {
        "message": "Códigos CIIU cargados correctamente",
        "municipality_id": municipality_id,
        "municipality_name": municipality.name,
        "created_count": created_count,
        "updated_count": updated_count,
        "existing_count": existing_count,
        "total_catalog": len(CIIU_CODES),
        "note": "Los códigos se crearon con tarifa 0%. Configure las tarifas desde el panel de administración."
    }


@router.put("/activities/{activity_id}/tax-rate")
async def update_activity_tax_rate(
    activity_id: int,
    tax_rate: float,
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Actualiza SOLO la tarifa de una actividad económica.
    
    Los códigos CIIU y descripciones son fijos del catálogo nacional
    y no pueden ser modificados. Solo la tarifa es editable.
    
    Args:
        activity_id: ID de la actividad
        tax_rate: Nueva tarifa (0-100%)
    """
    if tax_rate < 0 or tax_rate > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La tarifa debe estar entre 0 y 100"
        )
    
    activity = db.query(TaxActivity).filter(
        TaxActivity.id == activity_id
    ).first()
    
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actividad no encontrada"
        )
    
    # Verificar permisos
    if current_user.role == UserRole.ADMIN_ALCALDIA:
        if current_user.municipality_id != activity.municipality_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede modificar actividades de su municipio"
            )
    
    activity.tax_rate = tax_rate
    db.commit()
    db.refresh(activity)
    
    return {
        "message": "Tarifa actualizada correctamente",
        "activity": {
            "id": activity.id,
            "ciiu_code": activity.ciiu_code,
            "description": activity.description,
            "tax_rate": activity.tax_rate,
            "section_code": activity.section_code,
            "section_name": activity.section_name
        }
    }


@router.put("/activities/{municipality_id}/bulk-tax-rate")
async def bulk_update_tax_rates(
    municipality_id: int,
    updates: List[dict],
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Actualiza las tarifas de múltiples actividades en lote.
    
    Args:
        municipality_id: ID del municipio
        updates: Lista de objetos con {ciiu_code: str, tax_rate: float}
    
    Ejemplo de body:
    [
        {"ciiu_code": "0111", "tax_rate": 5.0},
        {"ciiu_code": "0112", "tax_rate": 4.5},
        ...
    ]
    """
    # Verificar permisos
    if current_user.role == UserRole.ADMIN_ALCALDIA:
        if current_user.municipality_id != municipality_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede modificar actividades de su municipio"
            )
    
    # Verificar que el municipio existe
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    updated_count = 0
    not_found = []
    errors = []
    
    for item in updates:
        ciiu_code = item.get('ciiu_code')
        tax_rate = item.get('tax_rate')
        
        if not ciiu_code:
            errors.append(f"Falta código CIIU en: {item}")
            continue
        
        if tax_rate is None:
            errors.append(f"Falta tarifa para código {ciiu_code}")
            continue
        
        try:
            tax_rate = float(tax_rate)
            if tax_rate < 0 or tax_rate > 100:
                errors.append(f"Tarifa inválida para {ciiu_code}: {tax_rate}")
                continue
        except (ValueError, TypeError):
            errors.append(f"Tarifa inválida para {ciiu_code}: {tax_rate}")
            continue
        
        activity = db.query(TaxActivity).filter(
            TaxActivity.municipality_id == municipality_id,
            TaxActivity.ciiu_code == ciiu_code
        ).first()
        
        if activity:
            activity.tax_rate = tax_rate
            updated_count += 1
        else:
            not_found.append(ciiu_code)
    
    db.commit()
    
    return {
        "message": "Actualización masiva de tarifas completada",
        "updated_count": updated_count,
        "not_found": not_found[:20] if not_found else None,
        "errors": errors[:20] if errors else None
    }


# ===================== GESTIÓN DE USUARIOS =====================

@router.get("/users", response_model=List[dict])
async def list_users(
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Lista usuarios según permisos del administrador.
    Incluye información del municipio asociado.
    """
    query = db.query(User).options(joinedload(User.municipality))
    
    if current_user.role == UserRole.ADMIN_ALCALDIA:
        query = query.filter(User.municipality_id == current_user.municipality_id)
    
    users = query.all()
    
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


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role: UserRole,
    current_user: User = Depends(require_role([UserRole.ADMIN_SISTEMA])),
    db: Session = Depends(get_db)
):
    """
    Actualiza el rol de un usuario.
    Solo administrador del sistema.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    user.role = role
    db.commit()
    
    return {"message": f"Rol actualizado a {role.value}"}


@router.put("/users/{user_id}/municipality")
async def assign_user_municipality(
    user_id: int,
    municipality_id: int,
    current_user: User = Depends(require_role([UserRole.ADMIN_SISTEMA])),
    db: Session = Depends(get_db)
):
    """
    Asigna un usuario a un municipio.
    Solo administrador del sistema.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    user.municipality_id = municipality_id
    db.commit()
    
    return {"message": f"Usuario asignado al municipio {municipality.name}"}


@router.post("/users", response_model=dict)
async def create_admin_user(
    user_data: AdminUserCreate,
    current_user: User = Depends(require_role([UserRole.ADMIN_SISTEMA])),
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo usuario administrador de alcaldía.
    Solo el super administrador (admin_sistema) puede crear estos usuarios.
    """
    # Verificar si el email ya existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )
    
    # Verificar que el municipio existe si se proporciona
    if user_data.municipality_id:
        municipality = db.query(Municipality).filter(
            Municipality.id == user_data.municipality_id
        ).first()
        if not municipality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Municipio no encontrado"
            )
    
    # Crear usuario con hash Argon2
    hashed_password = get_password_hash(user_data.password)
    
    # Convertir el rol del esquema al enum del modelo
    role_mapping = {
        'declarante': UserRole.DECLARANTE,
        'admin_alcaldia': UserRole.ADMIN_ALCALDIA,
        'admin_sistema': UserRole.ADMIN_SISTEMA
    }
    user_role = role_mapping.get(user_data.role.value, UserRole.ADMIN_ALCALDIA)
    
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        document_type=user_data.document_type,
        document_number=user_data.document_number,
        phone=user_data.phone,
        role=user_role,
        municipality_id=user_data.municipality_id
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role.value,
        "municipality_id": new_user.municipality_id,
        "is_active": new_user.is_active,
        "message": "Usuario administrador creado exitosamente"
    }


@router.put("/users/{user_id}/status")
async def toggle_user_status(
    user_id: int,
    status_data: UserStatusUpdate,
    current_user: User = Depends(require_role([UserRole.ADMIN_SISTEMA])),
    db: Session = Depends(get_db)
):
    """
    Activa o desactiva un usuario.
    Solo administrador del sistema.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # No permitir desactivar al propio usuario
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede desactivar su propia cuenta"
        )
    
    user.is_active = status_data.is_active
    db.commit()
    
    status_text = "activado" if status_data.is_active else "desactivado"
    return {"message": f"Usuario {status_text} correctamente"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_role([UserRole.ADMIN_SISTEMA])),
    db: Session = Depends(get_db)
):
    """
    Elimina permanentemente un usuario.
    Solo administrador del sistema.
    
    ADVERTENCIA: Esta acción es irreversible.
    Las declaraciones del usuario NO se eliminan (se mantienen para auditoría).
    Si el usuario tiene declaraciones asociadas, se debe usar la opción de desactivar
    en su lugar o eliminar primero las declaraciones.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # No permitir eliminar al propio usuario
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminar su propia cuenta"
        )
    
    # No permitir eliminar otros super admins
    if user.role == UserRole.ADMIN_SISTEMA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminar a otro super administrador"
        )
    
    # Verificar si el usuario tiene declaraciones
    declarations_count = db.query(ICADeclaration).filter(
        ICADeclaration.user_id == user_id
    ).count()
    
    if declarations_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar el usuario porque tiene {declarations_count} declaración(es) asociada(s). "
                   f"Primero elimine las declaraciones usando 'Limpiar Datos del Municipio' o desactive el usuario en su lugar."
        )
    
    # Guardar info para el mensaje
    user_email = user.email
    user_name = user.full_name
    user_municipality_id = user.municipality_id
    user_role = user.role
    
    try:
        # Limpiar referencias en audit_logs (set user_id to NULL)
        db.query(AuditLog).filter(AuditLog.user_id == user_id).update(
            {AuditLog.user_id: None},
            synchronize_session='fetch'
        )
        
        # Limpiar referencias en white_label_configs (updated_by)
        db.query(WhiteLabelConfig).filter(WhiteLabelConfig.updated_by == user_id).update(
            {WhiteLabelConfig.updated_by: None},
            synchronize_session='fetch'
        )
        
        # Limpiar referencias en formula_parameters (updated_by)
        db.query(FormulaParameters).filter(FormulaParameters.updated_by == user_id).update(
            {FormulaParameters.updated_by: None},
            synchronize_session='fetch'
        )
        
        # Si es un admin_alcaldia con municipio asignado, limpiar el municipality_id
        # de todos los usuarios declarantes asociados a ese municipio
        # Esto evita problemas con la generación de PDF cuando se elimina el admin
        # y se crea uno nuevo con un municipio diferente
        declarantes_updated = 0
        if user_role == UserRole.ADMIN_ALCALDIA and user_municipality_id is not None:
            declarantes_updated = db.query(User).filter(
                User.municipality_id == user_municipality_id,
                User.role == UserRole.DECLARANTE
            ).update(
                {User.municipality_id: None},
                synchronize_session=False
            )
            logger.info(f"Se limpiaron {declarantes_updated} declarantes del municipio {user_municipality_id}")
        
        # Eliminar el usuario
        db.delete(user)
        db.commit()
        
        response_data = {
            "message": f"Usuario {user_name} ({user_email}) eliminado correctamente",
            "deleted_user_id": user_id
        }
        
        # Si se limpiaron declarantes, incluir esa información
        if declarantes_updated > 0:
            response_data["declarantes_updated"] = declarantes_updated
            response_data["note"] = f"Se limpiaron {declarantes_updated} declarantes asociados al municipio del administrador eliminado"
        
        return response_data
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error al eliminar usuario {user_id}: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el usuario: {str(e)}"
        )


@router.delete("/municipalities/{municipality_id}/clean")
async def clean_municipality_data(
    municipality_id: int,
    current_user: User = Depends(require_role([UserRole.ADMIN_SISTEMA])),
    db: Session = Depends(get_db)
):
    """
    Limpia todos los datos de un municipio:
    - Elimina todas las declaraciones ICA
    - Elimina todos los usuarios declarantes asociados
    - Mantiene el municipio y su configuración de marca blanca
    
    Solo administrador del sistema.
    ADVERTENCIA: Esta acción es irreversible.
    """
    from ...models.models import ICADeclaration, Taxpayer, IncomeBase, TaxableActivity
    from ...models.models import EnergyGeneration, TaxSettlement, PaymentSection
    from ...models.models import DiscountsCredits, DeclarationResult, AuditLog
    
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    # Contar datos a eliminar
    declarations_count = db.query(ICADeclaration).filter(
        ICADeclaration.municipality_id == municipality_id
    ).count()
    
    declarantes_count = db.query(User).filter(
        User.municipality_id == municipality_id,
        User.role == UserRole.DECLARANTE
    ).count()
    
    # Eliminar declaraciones y sus datos relacionados
    declarations = db.query(ICADeclaration).filter(
        ICADeclaration.municipality_id == municipality_id
    ).all()
    
    for declaration in declarations:
        # Eliminar datos relacionados de cada declaración
        db.query(Taxpayer).filter(Taxpayer.declaration_id == declaration.id).delete()
        db.query(IncomeBase).filter(IncomeBase.declaration_id == declaration.id).delete()
        db.query(TaxableActivity).filter(TaxableActivity.declaration_id == declaration.id).delete()
        db.query(EnergyGeneration).filter(EnergyGeneration.declaration_id == declaration.id).delete()
        db.query(TaxSettlement).filter(TaxSettlement.declaration_id == declaration.id).delete()
        db.query(PaymentSection).filter(PaymentSection.declaration_id == declaration.id).delete()
        db.query(DiscountsCredits).filter(DiscountsCredits.declaration_id == declaration.id).delete()
        db.query(DeclarationResult).filter(DeclarationResult.declaration_id == declaration.id).delete()
        db.query(AuditLog).filter(AuditLog.declaration_id == declaration.id).delete()
    
    # Eliminar las declaraciones
    db.query(ICADeclaration).filter(
        ICADeclaration.municipality_id == municipality_id
    ).delete()
    
    # Eliminar usuarios declarantes del municipio
    db.query(User).filter(
        User.municipality_id == municipality_id,
        User.role == UserRole.DECLARANTE
    ).delete()
    
    db.commit()
    
    return {
        "message": f"Datos del municipio {municipality.name} limpiados correctamente",
        "municipality_id": municipality_id,
        "declarations_deleted": declarations_count,
        "users_deleted": declarantes_count
    }


# ===================== PARÁMETROS DE FÓRMULAS (EDICIÓN EN CALIENTE) =====================

@router.get("/formula-parameters/{municipality_id}", response_model=FormulaParametersResponse)
async def get_formula_parameters(
    municipality_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene los parámetros de fórmulas configurables de un municipio.
    Permite visualizar los valores numéricos que se usan en los cálculos.
    """
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    params = db.query(FormulaParameters).filter(
        FormulaParameters.municipality_id == municipality_id
    ).first()
    
    # Si no existen parámetros, crear unos por defecto
    if not params:
        params = FormulaParameters(municipality_id=municipality_id)
        db.add(params)
        db.commit()
        db.refresh(params)
    
    return params


@router.put("/formula-parameters/{municipality_id}", response_model=FormulaParametersResponse)
async def update_formula_parameters(
    municipality_id: int,
    data: FormulaParametersUpdate,
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Actualiza los parámetros de fórmulas de un municipio.
    
    EDICIÓN EN CALIENTE:
    Permite modificar valores numéricos de las fórmulas sin cambiar código,
    para adaptarse a cambios en legislación municipal.
    
    Parámetros configurables:
    - avisos_tableros_porcentaje: % sobre impuesto ICA para avisos y tableros
    - sobretasa_bomberil_porcentaje: % sobretasa bomberil
    - sobretasa_seguridad_porcentaje: % sobretasa seguridad
    - ley_56_tarifa_por_kw: Tarifa por kW instalado (Ley 56 de 1981)
    - anticipo_ano_siguiente_porcentaje: % anticipo año siguiente
    - descuento_pronto_pago_porcentaje: % descuento por pronto pago
    - descuento_pronto_pago_dias: Días para aplicar descuento pronto pago
    - interes_mora_mensual: % mensual de intereses por mora
    - unidades_adicionales_financiero_valor: Valor unidades comerciales adicionales financiero
    """
    # Verificar permisos para admin de alcaldía
    if current_user.role == UserRole.ADMIN_ALCALDIA:
        if current_user.municipality_id != municipality_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede modificar los parámetros de su municipio"
            )
    
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    params = db.query(FormulaParameters).filter(
        FormulaParameters.municipality_id == municipality_id
    ).first()
    
    if not params:
        # Crear nuevos parámetros
        params = FormulaParameters(
            municipality_id=municipality_id,
            updated_by=current_user.id
        )
        db.add(params)
    
    # Actualizar campos
    for key, value in data.dict(exclude_unset=True).items():
        setattr(params, key, value)
    
    params.updated_by = current_user.id
    
    db.commit()
    db.refresh(params)
    
    return params


@router.post("/formula-parameters", response_model=FormulaParametersResponse)
async def create_formula_parameters(
    data: FormulaParametersCreate,
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Crea parámetros de fórmulas para un municipio.
    """
    # Verificar permisos para admin de alcaldía
    if current_user.role == UserRole.ADMIN_ALCALDIA:
        if current_user.municipality_id != data.municipality_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede crear parámetros para su municipio"
            )
    
    # Verificar que el municipio existe
    municipality = db.query(Municipality).filter(
        Municipality.id == data.municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    # Verificar que no existan parámetros para este municipio
    existing = db.query(FormulaParameters).filter(
        FormulaParameters.municipality_id == data.municipality_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existen parámetros para este municipio. Use PUT para actualizarlos."
        )
    
    params = FormulaParameters(
        **data.dict(),
        updated_by=current_user.id
    )
    
    db.add(params)
    db.commit()
    db.refresh(params)
    
    return params


# ===================== BACKUP MANAGEMENT =====================

import json
import subprocess
from datetime import datetime
from fastapi.responses import FileResponse
from ...core.config import get_colombia_time


@router.get("/backups")
async def list_backups(
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Lista los backups disponibles.
    Los backups se almacenan en la carpeta de assets del sistema.
    """
    backups_path = os.path.join(settings.ASSETS_STORAGE_PATH, "backups")
    os.makedirs(backups_path, exist_ok=True)
    
    backups = []
    try:
        for filename in os.listdir(backups_path):
            if filename.endswith('.sql') or filename.endswith('.json'):
                filepath = os.path.join(backups_path, filename)
                stat = os.stat(filepath)
                backups.append({
                    "filename": filename,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": "sql" if filename.endswith('.sql') else "json"
                })
    except Exception as e:
        pass
    
    # Ordenar por fecha de creación descendente
    backups.sort(key=lambda x: x['created_at'], reverse=True)
    
    return {"backups": backups, "path": backups_path}


@router.post("/backups/create")
async def create_backup(
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Crea un backup de la base de datos.
    El backup se guarda como archivo SQL en el servidor.
    
    NOTA: Para sistemas on-premise, se recomienda también
    configurar backups automáticos a nivel de sistema operativo.
    """
    from ...core.config import settings
    
    backups_path = os.path.join(settings.ASSETS_STORAGE_PATH, "backups")
    os.makedirs(backups_path, exist_ok=True)
    
    # Generar nombre de archivo con timestamp de Colombia
    timestamp = get_colombia_time().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"ica_backup_{timestamp}.sql"
    backup_path = os.path.join(backups_path, backup_filename)
    
    # Extraer credenciales de DATABASE_URL
    db_url = settings.DATABASE_URL
    
    try:
        # Parsear DATABASE_URL
        # Formato: postgresql://user:password@host:port/database
        POSTGRESQL_PREFIX = 'postgresql://'
        if db_url.startswith(POSTGRESQL_PREFIX):
            db_url = db_url[len(POSTGRESQL_PREFIX):]  # Remove prefix
        
        # Validate and parse URL components
        if '@' not in db_url or '/' not in db_url:
            # Invalid URL format, fallback to JSON backup
            return await create_json_backup(db, backups_path, timestamp, current_user)
        
        user_pass, host_db = db_url.split('@', 1)
        
        if ':' not in user_pass:
            return await create_json_backup(db, backups_path, timestamp, current_user)
        
        db_user, db_password = user_pass.split(':', 1)
        host_port, db_name = host_db.split('/', 1)
        
        if ':' in host_port:
            db_host, db_port = host_port.split(':', 1)
        else:
            db_host = host_port
            db_port = '5432'
        
        # Validate parsed components (no shell metacharacters)
        import re
        safe_pattern = re.compile(r'^[a-zA-Z0-9_.\-]+$')
        if not all(safe_pattern.match(c) for c in [db_host, db_port, db_user, db_name] if c):
            return await create_json_backup(db, backups_path, timestamp, current_user)
        
        # Establecer variable de entorno para contraseña
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password
        
        # Ejecutar pg_dump with validated parameters
        cmd = [
            'pg_dump',
            '-h', db_host,
            '-p', db_port,
            '-U', db_user,
            '-d', db_name,
            '-f', backup_path,
            '--no-owner',
            '--no-privileges'
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            # Si pg_dump falla, crear backup JSON de tablas principales
            return await create_json_backup(db, backups_path, timestamp, current_user)
        
        # Obtener tamaño del archivo
        file_size = os.path.getsize(backup_path)
        
        return {
            "message": "Backup creado exitosamente",
            "filename": backup_filename,
            "path": backup_path,
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "created_at": get_colombia_time().isoformat(),
            "type": "sql"
        }
        
    except subprocess.TimeoutExpired:
        return await create_json_backup(db, backups_path, timestamp, current_user)
    except Exception as e:
        # Fallback a backup JSON
        return await create_json_backup(db, backups_path, timestamp, current_user)


async def create_json_backup(db: Session, backups_path: str, timestamp: str, current_user: User):
    """
    Crea un backup completo en formato JSON de las tablas principales.
    Usado como fallback cuando pg_dump no está disponible.
    Este backup es hotswap-ready (puede restaurarse sin intervención técnica).
    """
    from ...models.models import (
        ICADeclaration, Taxpayer, IncomeBase, TaxableActivity,
        TaxSettlement, PaymentSection, SignatureInfo, Municipality,
        WhiteLabelConfig, TaxActivity, FormulaParameters
    )
    
    backup_filename = f"ica_backup_{timestamp}.json"
    backup_path = os.path.join(backups_path, backup_filename)
    
    # Filtrar por municipio si es admin de alcaldía
    if current_user.role == UserRole.ADMIN_ALCALDIA:
        declarations = db.query(ICADeclaration).filter(
            ICADeclaration.municipality_id == current_user.municipality_id
        ).all()
        municipalities = db.query(Municipality).filter(
            Municipality.id == current_user.municipality_id
        ).all()
    else:
        declarations = db.query(ICADeclaration).all()
        municipalities = db.query(Municipality).all()
    
    # Construir datos del backup
    backup_data = {
        "backup_info": {
            "created_at": get_colombia_time().isoformat(),
            "created_by": current_user.email,
            "version": "2.0",
            "type": "complete",
            "total_declarations": len(declarations),
            "total_municipalities": len(municipalities)
        },
        "municipalities": [],
        "declarations": []
    }
    
    # Backup de municipios y configuraciones
    for muni in municipalities:
        muni_data = {
            "id": muni.id,
            "code": muni.code,
            "name": muni.name,
            "department": muni.department,
            "is_active": muni.is_active
        }
        
        # Configuración marca blanca
        if muni.config:
            muni_data["white_label_config"] = {
                "primary_color": muni.config.primary_color,
                "secondary_color": muni.config.secondary_color,
                "accent_color": muni.config.accent_color,
                "font_family": muni.config.font_family,
                "header_text": muni.config.header_text,
                "footer_text": muni.config.footer_text,
                "legal_notes": muni.config.legal_notes,
                "form_title": muni.config.form_title,
                "app_name": muni.config.app_name,
                "watermark_text": muni.config.watermark_text,
                "consecutivo_prefijo": muni.config.consecutivo_prefijo,
                "consecutivo_actual": muni.config.consecutivo_actual,
                "consecutivo_digitos": muni.config.consecutivo_digitos,
                "radicado_prefijo": muni.config.radicado_prefijo,
                "radicado_actual": muni.config.radicado_actual,
                "radicado_digitos": muni.config.radicado_digitos
            }
        
        # Parámetros de fórmulas
        if muni.formula_parameters:
            muni_data["formula_parameters"] = {
                "avisos_tableros_porcentaje": muni.formula_parameters.avisos_tableros_porcentaje,
                "sobretasa_bomberil_porcentaje": muni.formula_parameters.sobretasa_bomberil_porcentaje,
                "sobretasa_seguridad_porcentaje": muni.formula_parameters.sobretasa_seguridad_porcentaje,
                "ley_56_tarifa_por_kw": muni.formula_parameters.ley_56_tarifa_por_kw,
                "anticipo_ano_siguiente_porcentaje": muni.formula_parameters.anticipo_ano_siguiente_porcentaje,
                "descuento_pronto_pago_porcentaje": muni.formula_parameters.descuento_pronto_pago_porcentaje,
                "descuento_pronto_pago_dias": muni.formula_parameters.descuento_pronto_pago_dias,
                "interes_mora_mensual": muni.formula_parameters.interes_mora_mensual
            }
        
        # Actividades económicas
        activities = db.query(TaxActivity).filter(
            TaxActivity.municipality_id == muni.id,
            TaxActivity.is_active == True
        ).all()
        muni_data["tax_activities"] = [
            {
                "ciiu_code": act.ciiu_code,
                "description": act.description,
                "tax_rate": act.tax_rate
            }
            for act in activities
        ]
        
        backup_data["municipalities"].append(muni_data)
    
    # Backup de declaraciones
    for dec in declarations:
        dec_data = {
            "id": dec.id,
            "form_number": dec.form_number,
            "filing_number": dec.filing_number,
            "tax_year": dec.tax_year,
            "declaration_type": dec.declaration_type.value if dec.declaration_type else None,
            "status": dec.status.value if dec.status else None,
            "is_signed": dec.is_signed,
            "signed_at": dec.signed_at.isoformat() if dec.signed_at else None,
            "created_at": dec.created_at.isoformat() if dec.created_at else None,
            "municipality_id": dec.municipality_id,
            "user_id": dec.user_id
        }
        
        # Agregar datos del contribuyente
        if dec.taxpayer:
            dec_data["taxpayer"] = {
                "legal_name": dec.taxpayer.legal_name,
                "document_type": dec.taxpayer.document_type,
                "document_number": dec.taxpayer.document_number,
                "verification_digit": dec.taxpayer.verification_digit,
                "email": dec.taxpayer.email,
                "phone": dec.taxpayer.phone,
                "address": dec.taxpayer.address,
                "department": dec.taxpayer.department,
                "municipality": dec.taxpayer.municipality,
                "entity_type": dec.taxpayer.entity_type,
                "num_establishments": dec.taxpayer.num_establishments,
                "taxpayer_classification": dec.taxpayer.taxpayer_classification
            }
        
        # Agregar base de ingresos
        if dec.income_base:
            dec_data["income_base"] = {
                "row_8": dec.income_base.row_8_total_income_country,
                "row_9": dec.income_base.row_9_income_outside_municipality,
                "row_11": dec.income_base.row_11_returns_rebates_discounts,
                "row_12": dec.income_base.row_12_exports_fixed_assets,
                "row_13": dec.income_base.row_13_excluded_non_taxable,
                "row_14": dec.income_base.row_14_exempt_income
            }
        
        # Agregar actividades
        if dec.activities:
            dec_data["activities"] = [
                {
                    "activity_type": act.activity_type,
                    "ciiu_code": act.ciiu_code,
                    "description": act.description,
                    "income": act.income,
                    "tax_rate": act.tax_rate,
                    "special_rate": act.special_rate
                }
                for act in dec.activities
            ]
        
        # Agregar liquidación
        if dec.settlement:
            dec_data["settlement"] = {
                "row_20_total_ica_tax": dec.settlement.row_20_total_ica_tax,
                "row_21_signs_boards": dec.settlement.row_21_signs_boards,
                "row_22_financial_additional_units": dec.settlement.row_22_financial_additional_units,
                "row_23_bomberil_surcharge": dec.settlement.row_23_bomberil_surcharge,
                "row_24_security_surcharge": dec.settlement.row_24_security_surcharge,
                "row_26_exemptions": dec.settlement.row_26_exemptions,
                "row_27_withholdings_municipality": dec.settlement.row_27_withholdings_municipality,
                "row_28_self_withholdings": dec.settlement.row_28_self_withholdings,
                "row_29_previous_advance": dec.settlement.row_29_previous_advance,
                "row_30_next_year_advance": dec.settlement.row_30_next_year_advance,
                "row_31_penalties": dec.settlement.row_31_penalties,
                "row_32_previous_balance_favor": dec.settlement.row_32_previous_balance_favor
            }
        
        # Agregar sección de pago
        if dec.payment_section:
            dec_data["payment_section"] = {
                "row_36_early_payment_discount": dec.payment_section.row_36_early_payment_discount,
                "row_37_late_interest": dec.payment_section.row_37_late_interest,
                "row_39_voluntary_payment": dec.payment_section.row_39_voluntary_payment,
                "row_39_voluntary_destination": dec.payment_section.row_39_voluntary_destination
            }
        
        # Agregar información de firma
        if dec.signature_info:
            dec_data["signature_info"] = {
                "declarant_name": dec.signature_info.declarant_name,
                "declarant_document": dec.signature_info.declarant_document,
                "declarant_signature_method": dec.signature_info.declarant_signature_method,
                "declarant_oath_accepted": dec.signature_info.declarant_oath_accepted,
                "declaration_date": dec.signature_info.declaration_date.isoformat() if dec.signature_info.declaration_date else None,
                "requires_fiscal_reviewer": dec.signature_info.requires_fiscal_reviewer,
                "accountant_name": dec.signature_info.accountant_name,
                "accountant_document": dec.signature_info.accountant_document,
                "accountant_professional_card": dec.signature_info.accountant_professional_card,
                "signed_at": dec.signature_info.signed_at.isoformat() if dec.signature_info.signed_at else None
            }
        
        # Agregar resultado
        if dec.result:
            dec_data["result"] = {
                "amount_to_pay": dec.result.amount_to_pay,
                "balance_in_favor": dec.result.balance_in_favor
            }
        
        backup_data["declarations"].append(dec_data)
    
    # Guardar archivo JSON
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
    
    file_size = os.path.getsize(backup_path)
    
    return {
        "message": "Backup JSON completo creado exitosamente",
        "filename": backup_filename,
        "path": backup_path,
        "size_bytes": file_size,
        "size_mb": round(file_size / (1024 * 1024), 2),
        "created_at": get_colombia_time().isoformat(),
        "type": "json",
        "declarations_count": len(declarations),
        "municipalities_count": len(municipalities),
        "hotswap_ready": True
    }


@router.get("/backups/{filename}/download")
async def download_backup(
    filename: str,
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Descarga un archivo de backup.
    """
    backups_path = os.path.join(settings.ASSETS_STORAGE_PATH, "backups")
    filepath = os.path.join(backups_path, filename)
    
    # Validar que el archivo existe y está en la carpeta de backups
    if not os.path.exists(filepath) or not filepath.startswith(backups_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup no encontrado"
        )
    
    media_type = "application/sql" if filename.endswith('.sql') else "application/json"
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=media_type
    )


@router.post("/backups/upload")
async def upload_backup(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.ADMIN_SISTEMA])),
    db: Session = Depends(get_db)
):
    """
    Sube un archivo de backup al servidor.
    Solo el administrador del sistema puede subir backups.
    
    NOTA: La restauración de backups SQL debe hacerse manualmente
    desde la línea de comandos por seguridad.
    """
    # Validar tipo de archivo
    if not file.filename.endswith('.sql') and not file.filename.endswith('.json'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de archivo no permitido. Use archivos .sql o .json"
        )
    
    backups_path = os.path.join(settings.ASSETS_STORAGE_PATH, "backups")
    os.makedirs(backups_path, exist_ok=True)
    
    # Generar nombre único para evitar sobrescritura
    timestamp = get_colombia_time().strftime('%Y%m%d_%H%M%S')
    original_name = os.path.splitext(file.filename)[0]
    extension = os.path.splitext(file.filename)[1]
    new_filename = f"{original_name}_uploaded_{timestamp}{extension}"
    filepath = os.path.join(backups_path, new_filename)
    
    # Guardar archivo
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)
    
    file_size = os.path.getsize(filepath)
    
    return {
        "message": "Backup subido exitosamente",
        "original_filename": file.filename,
        "saved_filename": new_filename,
        "path": filepath,
        "size_bytes": file_size,
        "size_mb": round(file_size / (1024 * 1024), 2),
        "uploaded_at": get_colombia_time().isoformat(),
        "note": "Para restaurar un backup SQL, use el comando: psql -U usuario -d base_datos -f archivo.sql"
    }


@router.post("/backups/{filename}/restore")
async def restore_json_backup(
    filename: str,
    current_user: User = Depends(require_role([UserRole.ADMIN_SISTEMA])),
    db: Session = Depends(get_db)
):
    """
    Restaura un backup JSON (hotswap).
    Solo el administrador del sistema puede restaurar backups.
    
    IMPORTANTE: Esta operación restaura las declaraciones del backup JSON
    sin necesidad de intervención técnica. Ideal para cambios en caliente.
    
    - Solo restaura declaraciones que no existen en la base de datos actual
    - No sobrescribe declaraciones existentes
    - Registra el proceso en logs de auditoría
    """
    from ...models.models import (
        ICADeclaration, Taxpayer, IncomeBase, TaxableActivity,
        TaxSettlement, DeclarationResult, DeclarationType, FormStatus
    )
    
    # Solo permitir restauración de archivos JSON
    if not filename.endswith('.json'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden restaurar backups JSON. Los backups SQL requieren intervención técnica."
        )
    
    backups_path = os.path.join(settings.ASSETS_STORAGE_PATH, "backups")
    filepath = os.path.join(backups_path, filename)
    
    # Validar que el archivo existe y está en la carpeta de backups
    if not os.path.exists(filepath) or not filepath.startswith(backups_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup no encontrado"
        )
    
    try:
        # Leer archivo JSON
        with open(filepath, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        # Validar estructura del backup
        if 'backup_info' not in backup_data or 'declarations' not in backup_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de backup JSON inválido"
            )
        
        restored_count = 0
        skipped_count = 0
        errors = []
        
        for dec_data in backup_data.get('declarations', []):
            try:
                # Verificar si la declaración ya existe (por form_number)
                existing = db.query(ICADeclaration).filter(
                    ICADeclaration.form_number == dec_data.get('form_number')
                ).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Crear nueva declaración
                declaration_type = DeclarationType(dec_data.get('declaration_type', 'inicial'))
                status_value = FormStatus(dec_data.get('status', 'borrador'))
                
                # Preservar el user_id original del backup si existe, sino usar el usuario actual
                original_user_id = dec_data.get('user_id')
                
                declaration = ICADeclaration(
                    form_number=dec_data.get('form_number'),
                    filing_number=dec_data.get('filing_number'),
                    tax_year=dec_data.get('tax_year'),
                    declaration_type=declaration_type,
                    status=status_value,
                    is_signed=dec_data.get('is_signed', False),
                    municipality_id=dec_data.get('municipality_id'),
                    user_id=original_user_id if original_user_id else current_user.id
                )
                
                db.add(declaration)
                db.flush()  # Obtener ID
                
                # Restaurar contribuyente
                taxpayer_data = dec_data.get('taxpayer', {})
                if taxpayer_data:
                    taxpayer = Taxpayer(
                        declaration_id=declaration.id,
                        legal_name=taxpayer_data.get('legal_name') or '',
                        document_type=taxpayer_data.get('document_type') or '',
                        document_number=taxpayer_data.get('document_number') or '',
                        email=taxpayer_data.get('email') or '',
                        phone=taxpayer_data.get('phone') or '',
                        address=taxpayer_data.get('address') or ''
                    )
                    db.add(taxpayer)
                
                # Restaurar base de ingresos
                income_data = dec_data.get('income_base', {})
                if income_data:
                    income_base = IncomeBase(
                        declaration_id=declaration.id,
                        row_8_total_income_country=income_data.get('row_8', 0),
                        row_9_income_outside_municipality=income_data.get('row_9', 0),
                        row_11_returns_rebates_discounts=income_data.get('row_11', 0),
                        row_12_exports_fixed_assets=income_data.get('row_12', 0),
                        row_13_excluded_non_taxable=income_data.get('row_13', 0),
                        row_14_exempt_income=income_data.get('row_14', 0)
                    )
                    db.add(income_base)
                
                # Restaurar actividades
                for act_data in dec_data.get('activities', []):
                    activity = TaxableActivity(
                        declaration_id=declaration.id,
                        ciiu_code=act_data.get('ciiu_code', ''),
                        description=act_data.get('description', ''),
                        income=act_data.get('income', 0),
                        tax_rate=act_data.get('tax_rate', 0)
                    )
                    db.add(activity)
                
                # Crear settlement vacío
                settlement = TaxSettlement(declaration_id=declaration.id)
                db.add(settlement)
                
                # Crear result vacío
                result = DeclarationResult(declaration_id=declaration.id)
                db.add(result)
                
                restored_count += 1
                
            except Exception as e:
                errors.append(f"Error en declaración {dec_data.get('form_number', 'desconocido')}: {str(e)}")
                continue
        
        # Commit todos los cambios
        db.commit()
        
        # Log de auditoría
        from ...models.models import AuditLog
        audit_log = AuditLog(
            user_id=current_user.id,
            action="RESTORE_BACKUP",
            entity_type="Backup",
            new_values={
                'filename': filename,
                'restored_count': restored_count,
                'skipped_count': skipped_count,
                'errors_count': len(errors)
            }
        )
        db.add(audit_log)
        db.commit()
        
        return {
            "message": "Restauración completada",
            "filename": filename,
            "restored_count": restored_count,
            "skipped_count": skipped_count,
            "errors": errors if errors else None,
            "restored_at": get_colombia_time().isoformat()
        }
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no es un JSON válido"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al restaurar backup: {str(e)}"
        )


@router.delete("/backups/{filename}")
async def delete_backup(
    filename: str,
    current_user: User = Depends(require_role([UserRole.ADMIN_SISTEMA])),
    db: Session = Depends(get_db)
):
    """
    Elimina un archivo de backup.
    Solo el administrador del sistema puede eliminar backups.
    """
    backups_path = os.path.join(settings.ASSETS_STORAGE_PATH, "backups")
    filepath = os.path.join(backups_path, filename)
    
    # Validar que el archivo existe y está en la carpeta de backups
    if not os.path.exists(filepath) or not filepath.startswith(backups_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup no encontrado"
        )
    
    os.remove(filepath)
    
    return {
        "message": f"Backup {filename} eliminado correctamente",
        "deleted_at": get_colombia_time().isoformat()
    }
