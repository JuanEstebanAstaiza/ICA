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
    Crea un backup en formato JSON de las tablas principales.
    Usado como fallback cuando pg_dump no está disponible.
    """
    from ...models.models import (
        ICADeclaration, Taxpayer, IncomeBase, TaxableActivity,
        TaxSettlement, PaymentSection, SignatureInfo
    )
    
    backup_filename = f"ica_backup_{timestamp}.json"
    backup_path = os.path.join(backups_path, backup_filename)
    
    # Filtrar por municipio si es admin de alcaldía
    if current_user.role == UserRole.ADMIN_ALCALDIA:
        declarations = db.query(ICADeclaration).filter(
            ICADeclaration.municipality_id == current_user.municipality_id
        ).all()
    else:
        declarations = db.query(ICADeclaration).all()
    
    # Construir datos del backup
    backup_data = {
        "backup_info": {
            "created_at": get_colombia_time().isoformat(),
            "created_by": current_user.email,
            "version": "1.0",
            "total_declarations": len(declarations)
        },
        "declarations": []
    }
    
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
            "municipality_id": dec.municipality_id
        }
        
        # Agregar datos del contribuyente
        if dec.taxpayer:
            dec_data["taxpayer"] = {
                "legal_name": dec.taxpayer.legal_name,
                "document_type": dec.taxpayer.document_type,
                "document_number": dec.taxpayer.document_number,
                "email": dec.taxpayer.email,
                "phone": dec.taxpayer.phone,
                "address": dec.taxpayer.address
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
                    "ciiu_code": act.ciiu_code,
                    "description": act.description,
                    "income": act.income,
                    "tax_rate": act.tax_rate
                }
                for act in dec.activities
            ]
        
        backup_data["declarations"].append(dec_data)
    
    # Guardar archivo JSON
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
    
    file_size = os.path.getsize(backup_path)
    
    return {
        "message": "Backup JSON creado exitosamente",
        "filename": backup_filename,
        "path": backup_path,
        "size_bytes": file_size,
        "size_mb": round(file_size / (1024 * 1024), 2),
        "created_at": get_colombia_time().isoformat(),
        "type": "json",
        "declarations_count": len(declarations)
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
