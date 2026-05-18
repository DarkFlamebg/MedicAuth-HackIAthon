from fastapi import Request, HTTPException, status, Depends
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery
import time
from collections import defaultdict
from app.core.config import settings

# Historial de peticiones en memoria para Rate Limiting: IP -> List[timestamps]
request_history = defaultdict(list)

# Definimos los esquemas de API Key para query parameters o headers
api_key_query = APIKeyQuery(name="token", auto_error=False)
api_key_header = APIKeyHeader(name="X-Webhook-Token", auto_error=False)


def verify_webhook_token(
    token_q: str = Depends(api_key_query),
    token_h: str = Depends(api_key_header)
):
    """
    Verifica que el token recibido por query param o header coincida con el secreto.
    """
    expected_token = settings.WEBHOOK_SECRET_TOKEN
    if not expected_token:
        # Si no hay token configurado, permitimos el acceso por defecto
        return True
        
    if token_q == expected_token or token_h == expected_token:
        return True
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Acceso no autorizado: Token de webhook invalido o ausente."
    )


def rate_limiter_in_memory(times: int = 7, seconds: int = 1):
    """
    Rate Limiter en memoria RAM.
    Rastrea solicitudes por IP de cliente.
    """
    async def dependency(request: Request):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        # Limpiar registros más antiguos que la ventana de tiempo (seconds)
        request_history[ip] = [t for t in request_history[ip] if now - t < seconds]
        
        # Verificar si supera el límite de peticiones permitidas
        if len(request_history[ip]) >= times:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiadas peticiones. Por favor, intente mas tarde."
            )
        
        # Registrar marca de tiempo de la petición actual
        request_history[ip].append(now)
        return True
        
    return dependency
