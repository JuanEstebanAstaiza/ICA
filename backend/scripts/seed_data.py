#!/usr/bin/env python3
"""
Script para crear usuarios de prueba en la base de datos.
Ejecutar: python backend/scripts/seed_data.py
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path de Python
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine, Base
from app.models.models import User, UserRole
from app.core.security import get_password_hash


def seed_users(db: Session):
    """Crear usuarios de prueba."""
    
    # Lista de usuarios de prueba
    test_users = [
        {
            "email": "contribuyente@example.com",
            "password": "Test1234!",
            "full_name": "Juan Pérez Empresa SAS",
            "document_type": "NIT",
            "document_number": "900123456-7",
            "phone": "3001234567",
            "role": UserRole.DECLARANTE
        },
        {
            "email": "empresa@demo.com",
            "password": "Demo2024!",
            "full_name": "Comercial Demo LTDA",
            "document_type": "NIT",
            "document_number": "890456789-2",
            "phone": "3109876543",
            "role": UserRole.DECLARANTE
        },
        {
            "email": "admin@alcaldia.gov.co",
            "password": "Admin2024!",
            "full_name": "María González Administradora",
            "document_type": "CC",
            "document_number": "899999123-1",
            "phone": "3157891234",
            "role": UserRole.ADMIN_ALCALDIA
        },
        {
            "email": "superadmin@sistema.com",
            "password": "Super2024!",
            "full_name": "Carlos Rodríguez SuperAdmin",
            "document_type": "CC",
            "document_number": "800000000-0",
            "phone": "3201234567",
            "role": UserRole.ADMIN_SISTEMA
        }
    ]
    
    created_count = 0
    existing_count = 0
    
    # Crear cada usuario
    for user_data in test_users:
        # Verificar si el usuario ya existe
        existing_user = db.query(User).filter(
            User.email == user_data["email"]
        ).first()
        
        if not existing_user:
            # Hash de contraseña
            hashed_password = get_password_hash(user_data["password"])
            
            # Crear usuario
            user = User(
                email=user_data["email"],
                hashed_password=hashed_password,
                full_name=user_data["full_name"],
                document_type=user_data.get("document_type"),
                document_number=user_data.get("document_number"),
                phone=user_data.get("phone"),
                role=user_data["role"],
                is_active=True
            )
            
            db.add(user)
            created_count += 1
            print(f"✅ Usuario creado: {user_data['email']} ({user_data['role'].value})")
        else:
            existing_count += 1
            print(f"⚠️  Usuario ya existe: {user_data['email']}")
    
    return created_count, existing_count


def main():
    """Función principal."""
    print("=" * 60)
    print("🌱 SEED DATA - Sistema ICA")
    print("=" * 60)
    print("\nCreando datos de prueba...\n")
    
    # Crear tablas si no existen
    print("📋 Verificando tablas de base de datos...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas verificadas\n")
    
    # Crear sesión de base de datos
    db = SessionLocal()
    
    try:
        # Crear usuarios
        print("👥 Creando usuarios de prueba...")
        created, existing = seed_users(db)
        
        # Guardar cambios
        db.commit()
        
        print("\n" + "=" * 60)
        print("✅ PROCESO COMPLETADO")
        print("=" * 60)
        print(f"\n📊 Resumen:")
        print(f"   • Usuarios creados: {created}")
        print(f"   • Usuarios existentes: {existing}")
        print(f"   • Total procesados: {created + existing}")
        
        if created > 0:
            print("\n🎉 ¡Datos de prueba importados exitosamente!")
            print("\n📖 Credenciales de acceso:")
            print("\n   Usuario Contribuyente:")
            print("   - Email: contribuyente@example.com")
            print("   - Contraseña: Test1234!")
            print("\n   Usuario Empresa:")
            print("   - Email: empresa@demo.com")
            print("   - Contraseña: Demo2024!")
            print("\n   Admin Alcaldía:")
            print("   - Email: admin@alcaldia.gov.co")
            print("   - Contraseña: Admin2024!")
            print("\n   Super Admin:")
            print("   - Email: superadmin@sistema.com")
            print("   - Contraseña: Super2024!")
            print("\n📚 Ver más detalles en: docs/DATOS_PRUEBA.md")
        else:
            print("\nℹ️  No se crearon nuevos usuarios (todos ya existen)")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error al crear datos de prueba: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
