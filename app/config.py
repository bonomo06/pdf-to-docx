"""
Configurações da aplicação usando Pydantic Settings.
Carrega variáveis de ambiente do arquivo .env
"""

import secrets
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações da aplicação."""
    
    # Token de autenticação
    api_bearer_token: str = secrets.token_urlsafe(48)
    
    # Configurações de arquivo
    max_file_size_mb: int = 50
    
    # Configurações de segurança
    allowed_hosts: str = "*"
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 3600
    
    # Configurações da API
    api_title: str = "PDF to DOCX Converter API"
    api_version: str = "1.0.0"
    api_description: str = "API para conversão de documentos PDF para DOCX"
    
    @property
    def max_file_size_bytes(self) -> int:
        """Retorna o tamanho máximo do arquivo em bytes."""
        return self.max_file_size_mb * 1024 * 1024
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna instância cacheada das configurações.
    Usar cache para evitar recarregar o .env a cada request.
    """
    return Settings()
