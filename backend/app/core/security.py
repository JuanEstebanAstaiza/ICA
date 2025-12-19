"""
Módulo de seguridad - Autenticación JWT y hash de contraseñas con Argon2.
Implementa: security by design según requerimientos.
"""
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.hash import argon2
from fastapi import HTTPException, status
from .config import settings
import secrets
import hashlib


# Contexto de hash con Argon2 (requerimiento específico)
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=settings.ARGON2_TIME_COST,
    argon2__memory_cost=settings.ARGON2_MEMORY_COST,
    argon2__parallelism=settings.ARGON2_PARALLELISM
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash Argon2."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera hash Argon2 de una contraseña."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea un token JWT de acceso.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Crea un token JWT de refresco.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decodifica y valida un token JWT.
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def generate_csrf_token() -> str:
    """Genera un token CSRF seguro."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, session_token: str) -> bool:
    """Verifica un token CSRF."""
    return secrets.compare_digest(token, session_token)


def generate_integrity_hash(data: str) -> str:
    """
    Genera huella de integridad para documentos firmados.
    Usado para: "Se registra fecha, usuario y huella de integridad"
    """
    return hashlib.sha256(data.encode()).hexdigest()


def encrypt_sensitive_data(data: str, key: Optional[str] = None) -> str:
    """
    Cifrado de datos sensibles en reposo.
    Nota: En producción usar cryptography.fernet
    """
    # Placeholder - implementar con Fernet en producción
    return data


def decrypt_sensitive_data(encrypted_data: str, key: Optional[str] = None) -> str:
    """Descifrado de datos sensibles."""
    # Placeholder - implementar con Fernet en producción
    return encrypted_data
