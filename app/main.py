"""
API Principal para conversão de PDF para DOCX.
Implementa endpoints seguros com autenticação Bearer Token.
"""

import logging
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, HttpUrl, field_validator

from app.auth import verify_token
from app.config import get_settings
from app.converter import PDFConverterError, converter
from app.rate_limiter import rate_limiter

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação."""
    logger.info("Iniciando API PDF to DOCX Converter")
    yield
    logger.info("Encerrando API PDF to DOCX Converter")


# Inicialização da aplicação
settings = get_settings()

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Middlewares de segurança
if settings.allowed_hosts != "*":
    allowed_hosts = [h.strip() for h in settings.allowed_hosts.split(",")]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
)


# Schemas
class URLConvertRequest(BaseModel):
    """Schema para conversão via URL."""
    url: HttpUrl
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: HttpUrl) -> HttpUrl:
        """Valida se a URL parece ser de um PDF."""
        url_str = str(v).lower()
        # Permite URLs que terminam em .pdf ou que podem ser PDFs
        if not any(url_str.endswith(ext) for ext in [".pdf", ".pdf/"]):
            # Não bloqueia, pois algumas URLs de PDF não têm extensão
            pass
        return v


class HealthResponse(BaseModel):
    """Schema de resposta do health check."""
    status: str
    version: str


class ErrorResponse(BaseModel):
    """Schema de resposta de erro."""
    detail: str


# Dependency para autenticação
TokenDep = Annotated[str, Depends(verify_token)]


# Endpoints
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Verifica saúde da API"
)
async def health_check():
    """
    Endpoint de health check.
    Não requer autenticação.
    """
    return HealthResponse(status="healthy", version=settings.api_version)


@app.post(
    "/convert/file",
    tags=["Conversão"],
    summary="Converte PDF (upload) para DOCX",
    responses={
        200: {
            "description": "Arquivo DOCX convertido",
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            }
        },
        400: {"model": ErrorResponse, "description": "Arquivo inválido"},
        401: {"model": ErrorResponse, "description": "Não autorizado"},
        413: {"model": ErrorResponse, "description": "Arquivo muito grande"},
        429: {"model": ErrorResponse, "description": "Rate limit excedido"}
    }
)
async def convert_file(
    request: Request,
    token: TokenDep,
    file: UploadFile = File(..., description="Arquivo PDF para conversão")
):
    """
    Converte um arquivo PDF enviado por upload para DOCX.
    
    - **file**: Arquivo PDF (máximo 50MB por padrão)
    
    Retorna o arquivo DOCX convertido.
    """
    # Rate limiting
    await rate_limiter.check_rate_limit(request)
    
    # Validação do tipo de arquivo
    if file.content_type and file.content_type != "application/pdf":
        # Alguns clientes não enviam content-type correto, então verificamos o conteúdo
        pass
    
    # Lê o conteúdo do arquivo
    content = await file.read()
    
    # Validação de tamanho
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo muito grande. Máximo permitido: {settings.max_file_size_mb}MB"
        )
    
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio"
        )
    
    try:
        # Converte o PDF
        docx_content = await converter.convert_from_bytes(content)
        
        # Prepara o nome do arquivo de saída
        original_filename = file.filename or "document.pdf"
        output_filename = original_filename.rsplit(".", 1)[0] + ".docx"
        
        # Retorna o arquivo DOCX
        return Response(
            content=docx_content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"'
            }
        )
        
    except PDFConverterError as e:
        logger.error(f"Erro de conversão: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Erro inesperado durante conversão")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno durante a conversão"
        )


@app.post(
    "/convert/url",
    tags=["Conversão"],
    summary="Converte PDF (URL) para DOCX",
    responses={
        200: {
            "description": "Arquivo DOCX convertido",
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            }
        },
        400: {"model": ErrorResponse, "description": "URL ou arquivo inválido"},
        401: {"model": ErrorResponse, "description": "Não autorizado"},
        413: {"model": ErrorResponse, "description": "Arquivo muito grande"},
        429: {"model": ErrorResponse, "description": "Rate limit excedido"}
    }
)
async def convert_url(
    request: Request,
    token: TokenDep,
    body: URLConvertRequest
):
    """
    Converte um PDF de uma URL para DOCX.
    
    - **url**: URL do arquivo PDF
    
    Retorna o arquivo DOCX convertido.
    """
    # Rate limiting
    await rate_limiter.check_rate_limit(request)
    
    url_str = str(body.url)
    
    # Tratamento especial para Google Drive
    if "drive.google.com" in url_str or "docs.google.com" in url_str:
        # Extrai o ID do arquivo do Google Drive
        import re
        file_id = None
        
        # Padrões comuns de URL do Google Drive
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)',
            r'id=([a-zA-Z0-9_-]+)',
            r'/d/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_str)
            if match:
                file_id = match.group(1)
                break
        
        if file_id:
            # URL direta de download do Google Drive
            url_str = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    
    try:
        # Headers que simulam um navegador (necessário para alguns serviços)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf,*/*",
        }
        
        # Faz download do PDF com timeout e limite de tamanho
        async with httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
            max_redirects=10
        ) as client:
            # Faz download do arquivo
            response = await client.get(url_str, headers=headers)
            response.raise_for_status()
            
            content = response.content
            
            # Verifica se recebeu HTML ao invés de PDF (comum em Google Drive)
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type.lower():
                # Tenta extrair link de confirmação do Google Drive
                if b"confirm=" in content or b"download" in content.lower():
                    # Tenta com confirm=t
                    if "drive.google.com" in url_str:
                        confirm_url = url_str + ("&" if "?" in url_str else "?") + "confirm=t"
                        response = await client.get(confirm_url, headers=headers)
                        content = response.content
                        content_type = response.headers.get("content-type", "")
                
                if "text/html" in content_type.lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="A URL retornou uma página HTML ao invés do PDF. Para Google Drive, certifique-se que o arquivo é público e use o link de compartilhamento."
                    )
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Erro ao baixar PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao acessar URL: HTTP {e.response.status_code}"
        )
    except httpx.RequestError as e:
        logger.error(f"Erro de conexão: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao conectar com a URL fornecida"
        )
    except HTTPException:
        raise
    
    # Validação de tamanho (caso content-length não estivesse no header)
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo muito grande. Máximo permitido: {settings.max_file_size_mb}MB"
        )
    
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio ou URL não retornou conteúdo"
        )
    
    try:
        # Converte o PDF
        docx_content = await converter.convert_from_bytes(content)
        
        # Extrai nome do arquivo da URL
        url_path = str(body.url).split("?")[0]
        filename = url_path.split("/")[-1]
        if not filename.lower().endswith(".pdf"):
            filename = "document.pdf"
        output_filename = filename.rsplit(".", 1)[0] + ".docx"
        
        # Retorna o arquivo DOCX
        return Response(
            content=docx_content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"'
            }
        )
        
    except PDFConverterError as e:
        logger.error(f"Erro de conversão: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Erro inesperado durante conversão")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno durante a conversão"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
