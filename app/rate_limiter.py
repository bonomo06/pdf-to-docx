"""
Módulo de Rate Limiting para proteção contra abuso.
Implementa um rate limiter simples baseado em IP.
"""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import HTTPException, Request, status

from app.config import get_settings


class RateLimiter:
    """
    Rate limiter baseado em sliding window.
    Limita requisições por IP dentro de uma janela de tempo.
    """
    
    def __init__(self):
        # Dict[ip] = [(timestamp, count)]
        self._requests: Dict[str, list] = defaultdict(list)
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Obtém o IP real do cliente, considerando proxies.
        
        Args:
            request: Objeto Request do FastAPI
            
        Returns:
            IP do cliente
        """
        # Tenta obter IP de headers de proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Pega o primeiro IP (cliente original)
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback para IP direto
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _cleanup_old_requests(self, ip: str, window_seconds: int) -> None:
        """
        Remove requisições antigas fora da janela de tempo.
        
        Args:
            ip: IP do cliente
            window_seconds: Tamanho da janela em segundos
        """
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        self._requests[ip] = [
            ts for ts in self._requests[ip]
            if ts > cutoff_time
        ]
    
    async def check_rate_limit(self, request: Request) -> None:
        """
        Verifica se o cliente excedeu o rate limit.
        
        Args:
            request: Objeto Request do FastAPI
            
        Raises:
            HTTPException: Se o rate limit foi excedido
        """
        settings = get_settings()
        client_ip = self._get_client_ip(request)
        
        # Limpa requisições antigas
        self._cleanup_old_requests(client_ip, settings.rate_limit_window_seconds)
        
        # Verifica se excedeu o limite
        request_count = len(self._requests[client_ip])
        
        if request_count >= settings.rate_limit_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit excedido",
                    "message": f"Máximo de {settings.rate_limit_requests} requisições por {settings.rate_limit_window_seconds} segundos",
                    "retry_after": settings.rate_limit_window_seconds
                },
                headers={
                    "Retry-After": str(settings.rate_limit_window_seconds),
                    "X-RateLimit-Limit": str(settings.rate_limit_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + settings.rate_limit_window_seconds)
                }
            )
        
        # Registra a requisição
        self._requests[client_ip].append(time.time())
    
    def get_remaining_requests(self, request: Request) -> Tuple[int, int]:
        """
        Retorna informações sobre o rate limit atual.
        
        Args:
            request: Objeto Request do FastAPI
            
        Returns:
            Tupla (requisições restantes, tempo até reset)
        """
        settings = get_settings()
        client_ip = self._get_client_ip(request)
        
        self._cleanup_old_requests(client_ip, settings.rate_limit_window_seconds)
        
        request_count = len(self._requests[client_ip])
        remaining = max(0, settings.rate_limit_requests - request_count)
        
        if self._requests[client_ip]:
            oldest_request = min(self._requests[client_ip])
            reset_time = int(oldest_request + settings.rate_limit_window_seconds - time.time())
        else:
            reset_time = settings.rate_limit_window_seconds
        
        return remaining, max(0, reset_time)


# Instância global do rate limiter
rate_limiter = RateLimiter()
