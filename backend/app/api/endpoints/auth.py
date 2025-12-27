"""
Endpoints de autenticación.
Sistema de login institucional con JWT y Argon2.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ...db.database import get_db
from ...core.security import (
    verify_password, get_password_hash, 
    create_access_token, create_refresh_token,
    decode_token, generate_csrf_token
)
from ...core.config import get_colombia_time
from ...models.models import User, UserRole, PersonType, AuditLog, Municipality, WhiteLabelConfig
from ...schemas.schemas import (
    UserCreate, UserLogin, UserResponse, Token,
    UserRegisterNatural, UserRegisterJuridica, PersonTypeEnum
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Autenticación"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency para obtener el usuario actual desde el token JWT.
    """
    from sqlalchemy.orm import joinedload
    
    payload = decode_token(token)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
    # Eagerly load the municipality relationship to avoid lazy loading issues
    user = db.query(User).options(
        joinedload(User.municipality)
    ).filter(User.id == int(user_id)).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo"
        )
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verifica que el usuario esté activo."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    return current_user


def require_role(allowed_roles: list):
    """
    Dependency factory para verificar roles.
    Roles: declarante, admin_alcaldia, admin_sistema
    """
    def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para esta acción"
            )
        return current_user
    return role_checker


def get_platform_municipality(db: Session) -> Municipality:
    """
    Obtiene el municipio configurado para la plataforma.
    Como la plataforma no soporta multitenancy, debe haber solo un municipio activo
    con configuración de marca blanca.
    """
    # Buscar el municipio con configuración activa
    municipality = db.query(Municipality).join(
        WhiteLabelConfig, Municipality.config_id == WhiteLabelConfig.id
    ).filter(Municipality.is_active == True).first()
    
    if not municipality:
        # Si no hay ninguno con configuración, buscar cualquier admin de alcaldía
        # y usar su municipio
        admin = db.query(User).filter(
            User.role == UserRole.ADMIN_ALCALDIA,
            User.municipality_id.isnot(None)
        ).first()
        
        if admin:
            municipality = db.query(Municipality).filter(
                Municipality.id == admin.municipality_id
            ).first()
    
    return municipality


@router.get("/platform-municipality")
async def get_platform_municipality_info(db: Session = Depends(get_db)):
    """
    Obtiene la información del municipio configurado en la plataforma.
    Usado para autocompletar datos en el registro y formularios.
    """
    municipality = get_platform_municipality(db)
    
    if not municipality:
        return {"message": "Plataforma no configurada", "municipality": None}
    
    return {
        "municipality": {
            "id": municipality.id,
            "code": municipality.code,
            "name": municipality.name,
            "department": municipality.department
        }
    }


@router.get("/colombia-time")
async def get_colombia_time_endpoint():
    """
    Obtiene la fecha y hora actual en zona horaria de Colombia (UTC-5).
    Usado para sincronizar la hora en el frontend y asegurar que las 
    declaraciones se radiquen con la hora correcta de Colombia.
    """
    colombia_now = get_colombia_time()
    return {
        "datetime": colombia_now.isoformat(),
        "date": colombia_now.strftime('%Y-%m-%d'),
        "time": colombia_now.strftime('%H:%M:%S'),
        "formatted": colombia_now.strftime('%d/%m/%Y %H:%M:%S'),
        "timezone": "America/Bogota (UTC-5)"
    }


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Registro de nuevo usuario (legacy).
    """
    # Verificar si el email ya existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )
    
    # Obtener el municipio de la plataforma
    platform_municipality = get_platform_municipality(db)
    
    # Crear usuario con hash Argon2
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        document_type=user_data.document_type,
        document_number=user_data.document_number,
        phone=user_data.phone,
        address=user_data.address,
        role=UserRole.DECLARANTE,
        person_type=PersonType.NATURAL,
        municipality_id=platform_municipality.id if platform_municipality else None
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Log de auditoría
    audit_log = AuditLog(
        user_id=new_user.id,
        action="REGISTER",
        entity_type="User",
        entity_id=new_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    db.commit()
    
    return new_user


@router.post("/register/natural", response_model=UserResponse)
async def register_persona_natural(
    user_data: UserRegisterNatural,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Registro para PERSONA NATURAL.
    
    Los datos personales (nombre, documento, dirección) se usarán para
    autocompletar el formulario ICA del contribuyente.
    
    La dirección del municipio se autocompleta con el municipio configurado
    en la plataforma.
    """
    # Verificar si el email ya existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )
    
    # Verificar si el documento ya existe
    existing_doc = db.query(User).filter(
        User.document_number == user_data.document_number,
        User.document_type == user_data.document_type
    ).first()
    if existing_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con este número de documento"
        )
    
    # Obtener el municipio de la plataforma
    platform_municipality = get_platform_municipality(db)
    
    # Crear usuario con hash Argon2
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        document_type=user_data.document_type,
        document_number=user_data.document_number,
        phone=user_data.phone,
        address=user_data.address,
        nit=user_data.nit,  # NIT opcional para persona natural con actividad
        role=UserRole.DECLARANTE,
        person_type=PersonType.NATURAL,
        municipality_id=platform_municipality.id if platform_municipality else None
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Log de auditoría
    audit_log = AuditLog(
        user_id=new_user.id,
        action="REGISTER_NATURAL",
        entity_type="User",
        entity_id=new_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"person_type": "natural", "municipality_id": new_user.municipality_id}
    )
    db.add(audit_log)
    db.commit()
    
    # Enviar correo de bienvenida
    try:
        from ...services.email_service import email_service
        municipality_name = platform_municipality.name if platform_municipality else None
        email_service.send_registration_email(
            to_email=new_user.email,
            full_name=new_user.full_name,
            person_type="natural",
            document_type=new_user.document_type,
            document_number=new_user.document_number,
            municipality_name=municipality_name
        )
    except Exception as e:
        # No fallar el registro si el email falla
        logger.warning(f"Error sending registration email: {e}")
    
    return new_user


@router.post("/register/juridica", response_model=UserResponse)
async def register_persona_juridica(
    user_data: UserRegisterJuridica,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Registro para PERSONA JURÍDICA.
    
    Incluye datos de la empresa (razón social, NIT, dirección) y datos
    del representante legal (nombre, documento, email).
    
    El login se realiza con el email del representante legal.
    
    Los datos se usarán para autocompletar el formulario ICA:
    - Datos de la empresa como contribuyente
    - Datos del representante legal para la firma
    """
    # Verificar si el email del representante legal ya existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico del representante legal ya está registrado"
        )
    
    # Verificar si el NIT ya existe
    existing_nit = db.query(User).filter(User.nit == user_data.nit).first()
    if existing_nit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una empresa registrada con este NIT"
        )
    
    # Obtener el municipio de la plataforma
    platform_municipality = get_platform_municipality(db)
    
    # Crear usuario con hash Argon2
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        # Datos del representante legal (usado para login y firma)
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        document_type=user_data.document_type,
        document_number=user_data.document_number,
        phone=user_data.phone,
        address=user_data.address,
        
        # Datos de la empresa
        person_type=PersonType.JURIDICA,
        company_name=user_data.company_name,
        nit=user_data.nit,
        nit_verification_digit=user_data.nit_verification_digit,
        company_address=user_data.company_address,
        company_phone=user_data.company_phone,
        company_email=user_data.company_email,
        economic_activity=user_data.economic_activity,
        
        role=UserRole.DECLARANTE,
        municipality_id=platform_municipality.id if platform_municipality else None
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Log de auditoría
    audit_log = AuditLog(
        user_id=new_user.id,
        action="REGISTER_JURIDICA",
        entity_type="User",
        entity_id=new_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={
            "person_type": "juridica",
            "company_name": user_data.company_name,
            "nit": user_data.nit,
            "municipality_id": new_user.municipality_id
        }
    )
    db.add(audit_log)
    db.commit()
    
    # Enviar correo de bienvenida
    try:
        from ...services.email_service import email_service
        municipality_name = platform_municipality.name if platform_municipality else None
        email_service.send_registration_email(
            to_email=new_user.email,
            full_name=new_user.full_name,
            person_type="juridica",
            document_type=new_user.document_type,
            document_number=new_user.document_number,
            company_name=new_user.company_name,
            nit=new_user.nit,
            municipality_name=municipality_name
        )
    except Exception as e:
        # No fallar el registro si el email falla
        logger.warning(f"Error sending registration email: {e}")
    
    return new_user


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Inicio de sesión con generación de tokens JWT.
    """
    # Buscar usuario
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    # Actualizar último login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Generar tokens
    token_data = {"sub": str(user.id), "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Log de auditoría
    audit_log = AuditLog(
        user_id=user.id,
        action="LOGIN",
        entity_type="User",
        entity_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refresca el token de acceso usando el refresh token.
    """
    payload = decode_token(refresh_token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco inválido"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo"
        )
    
    # Generar nuevos tokens
    token_data = {"sub": str(user.id), "role": user.role.value}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtiene información del usuario autenticado.
    """
    return current_user


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cierre de sesión (registra el evento).
    Nota: La invalidación real del token debe manejarse en el cliente
    o con una lista negra en Redis.
    """
    # Log de auditoría
    audit_log = AuditLog(
        user_id=current_user.id,
        action="LOGOUT",
        entity_type="User",
        entity_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "Sesión cerrada correctamente"}


@router.get("/csrf-token")
async def get_csrf_token():
    """
    Genera un token CSRF para protección de formularios.
    """
    return {"csrf_token": generate_csrf_token()}
