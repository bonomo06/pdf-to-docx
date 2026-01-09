"""
Módulo de autenticação com Bearer Token.
Implementa validação segura do token usando comparação de tempo constante.
"""

import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

# Esquema de segurança HTTP Bearer
security = HTTPBearer(
    scheme_name="Bearer Token",
    description="Token de autenticação da API. Formato: Bearer <token>",
    auto_error=True
)


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Verifica se o token Bearer é válido.
    
    Usa comparação de tempo constante para prevenir timing attacks.
    
    Args:
        credentials: Credenciais HTTP com o token Bearer
        
    Returns:
        O token validado
        
    Raises:
        HTTPException: Se o token for inválido ou não fornecido
    """
    settings = get_settings()
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Comparação de tempo constante para prevenir timing attacks
    token_valid = secrets.compare_digest(
        credentials.credentials.encode("utf-8"),
        settings.api_bearer_token.encode("utf-8")
    )
    
    if not token_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação inválido",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return credentials.credentials
