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
from app.models.models import User, UserRole, PersonType
from app.core.security import get_password_hash


def seed_users(db: Session):
    """Crear usuarios de prueba."""
    
    # Lista de usuarios de prueba
    test_users = [
        # Usuario PERSONA NATURAL
        {
            "email": "contribuyente@example.com",
            "password": "Contrib2024!",
            "full_name": "Juan Carlos Pérez García",
            "document_type": "CC",
            "document_number": "1234567890",
            "phone": "3001234567",
            "address": "Carrera 15 #45-67, Barrio Centro",
            "role": UserRole.DECLARANTE,
            "person_type": PersonType.NATURAL
        },
        # Usuario PERSONA JURÍDICA (Empresa)
        {
            "email": "empresa@demo.com",
            "password": "Empresa2024!",
            "full_name": "Pedro Martínez López",  # Representante Legal
            "document_type": "CC",
            "document_number": "9876543210",
            "phone": "3109876543",
            "role": UserRole.DECLARANTE,
            "person_type": PersonType.JURIDICA,
            # Datos de la empresa
            "company_name": "Comercial Demo S.A.S.",
            "nit": "890456789",
            "nit_verification_digit": "2",
            "company_address": "Calle 100 #15-20, Zona Industrial",
            "company_phone": "6012345678",
            "company_email": "contacto@comercialdemo.com",
            "economic_activity": "Comercio al por mayor"
        },
        # Administrador de Alcaldía
        {
            "email": "admin@alcaldia.gov.co",
            "password": "Admin2024!",
            "full_name": "María González Administradora",
            "document_type": "CC",
            "document_number": "52345678",
            "phone": "3157891234",
            "role": UserRole.ADMIN_ALCALDIA,
            "person_type": PersonType.NATURAL
        },
        # Super Administrador del Sistema
        {
            "email": "superadmin@sistema.com",
            "password": "Super2024!",
            "full_name": "Carlos Rodríguez SuperAdmin",
            "document_type": "CC",
            "document_number": "11223344",
            "phone": "3201234567",
            "role": UserRole.ADMIN_SISTEMA,
            "person_type": PersonType.NATURAL
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
            
            # Crear usuario con todos los campos
            user = User(
                email=user_data["email"],
                hashed_password=hashed_password,
                full_name=user_data["full_name"],
                document_type=user_data.get("document_type"),
                document_number=user_data.get("document_number"),
                phone=user_data.get("phone"),
                address=user_data.get("address"),
                role=user_data["role"],
                is_active=True,
                # Tipo de persona
                person_type=user_data.get("person_type", PersonType.NATURAL),
                # Campos persona jurídica
                company_name=user_data.get("company_name"),
                nit=user_data.get("nit"),
                nit_verification_digit=user_data.get("nit_verification_digit"),
                company_address=user_data.get("company_address"),
                company_phone=user_data.get("company_phone"),
                company_email=user_data.get("company_email"),
                economic_activity=user_data.get("economic_activity")
            )
            
            db.add(user)
            created_count += 1
            person_type = user_data.get("person_type", PersonType.NATURAL)
            print(f"✅ Usuario creado: {user_data['email']} ({user_data['role'].value}) - Tipo: {person_type.value}")
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
            print("\n   👤 PERSONA NATURAL (Contribuyente):")
            print("   - Email: contribuyente@example.com")
            print("   - Contraseña: Contrib2024!")
            print("   - Nombre: Juan Carlos Pérez García")
            print("   - Documento: CC 1234567890")
            print("\n   🏢 PERSONA JURÍDICA (Empresa):")
            print("   - Email: empresa@demo.com")
            print("   - Contraseña: Empresa2024!")
            print("   - Empresa: Comercial Demo S.A.S.")
            print("   - NIT: 890456789-2")
            print("   - Rep. Legal: Pedro Martínez López")
            print("\n   🏛️ Admin Alcaldía:")
            print("   - Email: admin@alcaldia.gov.co")
            print("   - Contraseña: Admin2024!")
            print("\n   👑 Super Admin:")
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
