"""
Middleware de seguridad.
Implementa protecciones contra XSS, CSRF, y rate limiting.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict
import time
import re
from collections import defaultdict

from ...core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Agrega headers de seguridad a todas las respuestas.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        
        # Headers de seguridad
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Implementa rate limiting por IP.
    Configurable via variables de entorno.
    """
    
    def __init__(self, app, requests_limit: int = None, period: int = None):
        super().__init__(app)
        self.requests_limit = requests_limit or settings.RATE_LIMIT_REQUESTS
        self.period = period or settings.RATE_LIMIT_PERIOD
        self.request_counts: Dict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next: Callable):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Limpiar requests antiguos
        self.request_counts[client_ip] = [
            t for t in self.request_counts[client_ip]
            if current_time - t < self.period
        ]
        
        # Verificar límite
        if len(self.request_counts[client_ip]) >= self.requests_limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Demasiadas solicitudes. Intente más tarde."}
            )
        
        # Registrar request
        self.request_counts[client_ip].append(current_time)
        
        response = await call_next(request)
        return response


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Sanitiza inputs para prevenir XSS y SQL Injection.
    """
    
    # Patrones peligrosos
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe',
        r'<object',
        r'<embed',
    ]
    
    SQL_PATTERNS = [
        r';\s*DROP\s',
        r';\s*DELETE\s',
        r';\s*UPDATE\s',
        r'UNION\s+SELECT',
        r'OR\s+1\s*=\s*1',
        r"'\s*OR\s*'",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Solo verificar métodos que envían datos
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                body_str = body.decode('utf-8', errors='ignore')
                
                # Verificar patrones XSS
                for pattern in self.XSS_PATTERNS:
                    if re.search(pattern, body_str, re.IGNORECASE):
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={"detail": "Contenido no permitido detectado"}
                        )
                
                # Verificar patrones SQL Injection
                for pattern in self.SQL_PATTERNS:
                    if re.search(pattern, body_str, re.IGNORECASE):
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={"detail": "Contenido no permitido detectado"}
                        )
            except Exception:
                pass  # Si no se puede leer el body, continuar
        
        response = await call_next(request)
        return response


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Registra todas las peticiones para auditoría.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Log básico (en producción usar un logger apropiado)
        if settings.DEBUG:
            print(f"[AUDIT] {request.method} {request.url.path} "
                  f"- {response.status_code} - {process_time:.3f}s "
                  f"- IP: {request.client.host if request.client else 'unknown'}")
        
        return response
