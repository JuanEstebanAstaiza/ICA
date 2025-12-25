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
    User, UserRole, Municipality, WhiteLabelConfig, TaxActivity, FormulaParameters
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
        config = WhiteLabelConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
        
        municipality.config_id = config.id
        db.commit()
        db.refresh(municipality)
    
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
    
    # Guardar info para el mensaje
    user_email = user.email
    user_name = user.full_name
    
    # Eliminar el usuario
    db.delete(user)
    db.commit()
    
    return {
        "message": f"Usuario {user_name} ({user_email}) eliminado correctamente",
        "deleted_user_id": user_id
    }


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
