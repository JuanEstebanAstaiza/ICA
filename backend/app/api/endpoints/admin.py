"""
Endpoints para administración de alcaldías y configuración marca blanca.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import os
import uuid

from ...db.database import get_db
from ...models.models import (
    User, UserRole, Municipality, WhiteLabelConfig, TaxActivity
)
from ...schemas.schemas import (
    MunicipalityCreate, MunicipalityResponse,
    WhiteLabelConfigUpdate, WhiteLabelConfigResponse,
    TaxActivityCreate, TaxActivityResponse
)
from ...core.config import settings
from .auth import get_current_active_user, require_role

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


# ===================== CONFIGURACIÓN MARCA BLANCA =====================

@router.get("/white-label/{municipality_id}", response_model=WhiteLabelConfigResponse)
async def get_white_label_config(
    municipality_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene la configuración marca blanca de un municipio.
    """
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Municipio no encontrado"
        )
    
    if not municipality.config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración no encontrada"
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
        config = WhiteLabelConfig()
        db.add(config)
        db.commit()
        municipality.config_id = config.id
    
    # Actualizar campos
    for key, value in data.dict(exclude_unset=True).items():
        setattr(config, key, value)
    
    config.updated_by = current_user.id
    
    db.commit()
    db.refresh(config)
    
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


# ===================== ACTIVIDADES ECONÓMICAS =====================

@router.post("/activities", response_model=TaxActivityResponse)
async def create_tax_activity(
    data: TaxActivityCreate,
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Crea una actividad económica con su tarifa ICA.
    Catálogo CIIU por municipio.
    """
    # Verificar permisos
    if current_user.role == UserRole.ADMIN_ALCALDIA:
        if current_user.municipality_id != data.municipality_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede crear actividades para su municipio"
            )
    
    activity = TaxActivity(
        municipality_id=data.municipality_id,
        ciiu_code=data.ciiu_code,
        description=data.description,
        tax_rate=data.tax_rate
    )
    
    db.add(activity)
    db.commit()
    db.refresh(activity)
    
    return activity


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


@router.put("/activities/{activity_id}", response_model=TaxActivityResponse)
async def update_tax_activity(
    activity_id: int,
    data: TaxActivityCreate,
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Actualiza una actividad económica.
    """
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
    
    activity.ciiu_code = data.ciiu_code
    activity.description = data.description
    activity.tax_rate = data.tax_rate
    
    db.commit()
    db.refresh(activity)
    
    return activity


@router.delete("/activities/{activity_id}")
async def delete_tax_activity(
    activity_id: int,
    current_user: User = Depends(require_role([
        UserRole.ADMIN_ALCALDIA, 
        UserRole.ADMIN_SISTEMA
    ])),
    db: Session = Depends(get_db)
):
    """
    Desactiva una actividad económica (soft delete).
    """
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
                detail="Solo puede eliminar actividades de su municipio"
            )
    
    activity.is_active = False
    db.commit()
    
    return {"message": "Actividad desactivada correctamente"}


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
    """
    query = db.query(User)
    
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
            "municipality_id": u.municipality_id
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
