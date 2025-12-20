#!/usr/bin/env python3
"""
Script para cargar todos los municipios de Colombia con códigos DANE.
Ejecutar: python backend/scripts/seed_municipalities.py

Este script carga los 1,122 municipios de Colombia organizados por departamento.
Los datos provienen de la División Político-Administrativa (Divipola) del DANE.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path de Python
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine, Base
from app.models.models import Municipality

# Importar datos de municipios
from scripts.municipalities_data import MUNICIPIOS_COLOMBIA, DEPARTAMENTOS_COLOMBIA


def seed_municipalities(db: Session):
    """Crear todos los municipios de Colombia."""
    
    created_count = 0
    updated_count = 0
    
    print(f"\n📊 Departamentos a procesar: {len(DEPARTAMENTOS_COLOMBIA)}")
    print(f"📊 Municipios totales: {len(MUNICIPIOS_COLOMBIA)}")
    print("-" * 50)
    
    for codigo, nombre, departamento in MUNICIPIOS_COLOMBIA:
        # Verificar si el municipio ya existe
        existing = db.query(Municipality).filter(
            Municipality.code == codigo
        ).first()
        
        if existing:
            # Actualizar si hay cambios (edición en caliente)
            if existing.name != nombre or existing.department != departamento:
                existing.name = nombre
                existing.department = departamento
                updated_count += 1
        else:
            # Crear nuevo municipio
            municipality = Municipality(
                code=codigo,
                name=nombre,
                department=departamento,
                is_active=True
            )
            db.add(municipality)
            created_count += 1
    
    return created_count, updated_count


def print_resumen_por_departamento(db: Session):
    """Imprimir resumen de municipios por departamento."""
    print("\n📊 RESUMEN POR DEPARTAMENTO:")
    print("-" * 50)
    
    for dept in DEPARTAMENTOS_COLOMBIA:
        count = db.query(Municipality).filter(
            Municipality.department == dept
        ).count()
        print(f"   {dept}: {count} municipios")


def main():
    """Función principal."""
    print("=" * 60)
    print("🏛️  SEED MUNICIPIOS - Sistema ICA")
    print("    Carga de Municipios de Colombia (Códigos DANE)")
    print("=" * 60)
    
    # Crear tablas si no existen
    print("\n📋 Verificando tablas de base de datos...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas verificadas")
    
    # Crear sesión de base de datos
    db = SessionLocal()
    
    try:
        # Cargar municipios
        print("\n🏙️  Cargando municipios de Colombia...")
        created, updated = seed_municipalities(db)
        
        # Guardar cambios
        db.commit()
        
        # Mostrar resumen
        print("\n" + "=" * 60)
        print("✅ PROCESO COMPLETADO")
        print("=" * 60)
        print(f"\n📊 Resumen:")
        print(f"   • Municipios nuevos: {created}")
        print(f"   • Municipios actualizados: {updated}")
        print(f"   • Total en base de datos: {db.query(Municipality).count()}")
        
        # Opcional: mostrar resumen por departamento
        if created > 0:
            print_resumen_por_departamento(db)
        
        print("\n🎉 ¡Municipios cargados exitosamente!")
        print("\n💡 Los administradores de alcaldía ahora pueden")
        print("   seleccionar su municipio desde el panel de administración.")
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error al cargar municipios: {e}")
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

