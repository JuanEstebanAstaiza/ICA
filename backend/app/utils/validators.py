"""
Utilidades de validación.
Implementa validación estricta de inputs según requerimientos de seguridad.
"""
import re
from typing import Optional
from datetime import date


def validate_nit(nit: str, verification_digit: Optional[str] = None) -> bool:
    """
    Valida un NIT colombiano con su dígito de verificación.
    """
    if not nit or not nit.isdigit():
        return False
    
    if verification_digit is None:
        return True
    
    # Algoritmo de verificación del NIT
    weights = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
    nit_digits = [int(d) for d in nit.zfill(15)]
    
    total = sum(d * w for d, w in zip(nit_digits, weights))
    remainder = total % 11
    
    if remainder > 1:
        calculated_dv = 11 - remainder
    else:
        calculated_dv = remainder
    
    return str(calculated_dv) == verification_digit


def validate_email(email: str) -> bool:
    """Valida formato de email."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Valida formato de teléfono colombiano."""
    # Limpia el número
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Debe tener entre 7 y 12 dígitos
    if not clean_phone.isdigit():
        return False
    
    return 7 <= len(clean_phone) <= 12


def validate_ciiu_code(code: str) -> bool:
    """
    Valida formato de código CIIU.
    Los códigos CIIU son alfanuméricos de 4-6 caracteres.
    """
    if not code:
        return False
    
    # Debe ser alfanumérico
    if not re.match(r'^[A-Z0-9]{1,6}$', code.upper()):
        return False
    
    return True


def validate_tax_year(year: int) -> bool:
    """
    Valida que el año gravable sea válido.
    """
    current_year = date.today().year
    
    # El año debe ser razonable (no muy antiguo ni futuro)
    return 2000 <= year <= current_year + 1


def validate_monetary_amount(amount: float) -> bool:
    """
    Valida que un monto monetario sea válido.
    """
    if amount < 0:
        return False
    
    # Máximo razonable para evitar overflow
    if amount > 999_999_999_999:
        return False
    
    return True


def validate_tax_rate(rate: float) -> bool:
    """
    Valida que una tarifa ICA sea válida.
    Las tarifas se expresan en por mil.
    """
    # Las tarifas ICA típicamente van de 0 a 14 por mil
    return 0 <= rate <= 100


def sanitize_string(value: str) -> str:
    """
    Sanitiza un string para prevenir XSS.
    """
    if not value:
        return value
    
    # Reemplazar caracteres peligrosos
    replacements = {
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;',
        '\\': '&#x5C;',
    }
    
    for char, replacement in replacements.items():
        value = value.replace(char, replacement)
    
    return value


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza un nombre de archivo para prevenir path traversal.
    """
    if not filename:
        return filename
    
    # Eliminar caracteres peligrosos
    filename = re.sub(r'[/\\:*?"<>|]', '', filename)
    
    # Eliminar intentos de path traversal
    filename = filename.replace('..', '')
    
    return filename
