# Scripts de Utilidad

Este directorio contiene scripts de utilidad para el Sistema ICA.

## seed_data.py

Script para poblar la base de datos con usuarios de prueba.

### Uso

Con Docker:
```bash
docker compose exec backend python scripts/seed_data.py
```

Sin Docker:
```bash
cd backend
source venv/bin/activate  # En Windows: venv\Scripts\activate
python scripts/seed_data.py
```

### Usuarios Creados

El script crea los siguientes usuarios:

1. **Contribuyente** - contribuyente@example.com / Test1234!
2. **Empresa Demo** - empresa@demo.com / Demo2024!
3. **Admin Alcaldía** - admin@alcaldia.gov.co / Admin2024!
4. **Super Admin** - superadmin@sistema.com / Super2024!

Ver más detalles en `docs/DATOS_PRUEBA.md`
