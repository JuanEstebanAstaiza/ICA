#!/usr/bin/env python3
"""
Script para cargar todos los códigos CIIU nacionales de 4 dígitos para un municipio.
Los códigos CIIU vienen precargados y organizados por secciones (A-U).
Solo la tarifa (tax_rate) es editable por el administrador.

Ejecutar: python backend/scripts/seed_ciiu_codes.py [municipality_id]

Si no se proporciona municipality_id, se cargará para todos los municipios.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path de Python
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine, Base
from app.models.models import Municipality, TaxActivity
from scripts.ciiu_codes_data import CIIU_CODES, CIIU_SECTIONS


def seed_ciiu_codes_for_municipality(db: Session, municipality_id: int, municipality_name: str = None):
    """
    Carga todos los códigos CIIU para un municipio específico.
    Solo crea los códigos que no existen. No sobrescribe existentes.
    
    Args:
        db: Sesión de base de datos
        municipality_id: ID del municipio
        municipality_name: Nombre del municipio (solo para mostrar)
    
    Returns:
        Tuple (created_count, existing_count, updated_count)
    """
    created_count = 0
    existing_count = 0
    updated_count = 0
    
    for ciiu in CIIU_CODES:
        # Verificar si ya existe este código CIIU para el municipio
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
            # Crear nueva actividad con tarifa 0 (el admin debe configurarla)
            activity = TaxActivity(
                municipality_id=municipality_id,
                ciiu_code=ciiu['ciiu_code'],
                description=ciiu['description'],
                tax_rate=0.0,  # Tarifa inicial 0% - debe ser configurada por el admin
                section_code=ciiu['section_code'],
                section_name=ciiu['section_name'],
                is_active=True
            )
            db.add(activity)
            created_count += 1
    
    return created_count, existing_count, updated_count


def main():
    """Función principal."""
    print("=" * 70)
    print("🏷️  SEED CIIU CODES - Sistema ICA")
    print("=" * 70)
    print(f"\nCatálogo Nacional: {len(CIIU_CODES)} códigos CIIU de 4 dígitos")
    print(f"Secciones: {len(CIIU_SECTIONS)} (A hasta U)")
    print()
    
    # Crear tablas si no existen
    print("📋 Verificando tablas de base de datos...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas verificadas\n")
    
    # Crear sesión de base de datos
    db = SessionLocal()
    
    try:
        # Determinar qué municipios procesar
        municipality_id = None
        if len(sys.argv) > 1:
            try:
                municipality_id = int(sys.argv[1])
            except ValueError:
                print(f"❌ Error: El ID del municipio debe ser un número: {sys.argv[1]}")
                return 1
        
        if municipality_id:
            # Procesar solo un municipio
            municipality = db.query(Municipality).filter(Municipality.id == municipality_id).first()
            if not municipality:
                print(f"❌ Error: No existe el municipio con ID {municipality_id}")
                return 1
            
            municipalities = [municipality]
        else:
            # Procesar todos los municipios
            municipalities = db.query(Municipality).filter(Municipality.is_active == True).all()
            if not municipalities:
                print("⚠️  No hay municipios registrados en el sistema.")
                print("   Primero ejecute: python backend/scripts/seed_municipalities.py")
                return 1
        
        print(f"📍 Municipios a procesar: {len(municipalities)}")
        print()
        
        total_created = 0
        total_existing = 0
        total_updated = 0
        
        for municipality in municipalities:
            print(f"  🏛️  {municipality.name} ({municipality.department})...")
            created, existing, updated = seed_ciiu_codes_for_municipality(
                db, municipality.id, municipality.name
            )
            total_created += created
            total_existing += existing
            total_updated += updated
            
            if created > 0:
                print(f"      ✅ {created} códigos creados")
            if updated > 0:
                print(f"      🔄 {updated} códigos actualizados (sección)")
            if existing > 0 and created == 0 and updated == 0:
                print(f"      ℹ️  {existing} códigos ya existían")
        
        # Guardar cambios
        db.commit()
        
        print("\n" + "=" * 70)
        print("✅ PROCESO COMPLETADO")
        print("=" * 70)
        print(f"\n📊 Resumen:")
        print(f"   • Municipios procesados: {len(municipalities)}")
        print(f"   • Códigos CIIU creados: {total_created}")
        print(f"   • Códigos CIIU actualizados: {total_updated}")
        print(f"   • Códigos CIIU existentes: {total_existing}")
        
        if total_created > 0:
            print("\n🎉 ¡Códigos CIIU cargados exitosamente!")
            print("\n⚠️  IMPORTANTE:")
            print("   Los códigos se crearon con tarifa 0%.")
            print("   El administrador debe configurar las tarifas desde el panel de admin.")
        
        print("\n📖 Secciones disponibles:")
        for code, name in sorted(CIIU_SECTIONS.items()):
            count = len([c for c in CIIU_CODES if c['section_code'] == code])
            print(f"   • {code}: {name[:50]}... ({count} códigos)")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
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
