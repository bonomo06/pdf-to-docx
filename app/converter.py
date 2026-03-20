"""
Módulo de conversão de PDF para DOCX.
Implementa a lógica de conversão com validações de segurança.
"""

import os
import uuid
import tempfile
import logging
from pathlib import Path
from typing import BinaryIO

from pdf2docx import Converter

logger = logging.getLogger(__name__)


class PDFConverterError(Exception):
    """Exceção customizada para erros de conversão."""
    pass


class PDFToDocxConverter:
    """
    Classe para conversão de PDF para DOCX.
    Gerencia arquivos temporários de forma segura.
    """
    
    # Magic bytes para validação de PDF
    PDF_MAGIC_BYTES = b"%PDF"
    
    def __init__(self, temp_dir: str | None = None):
        """
        Inicializa o conversor.
        
        Args:
            temp_dir: Diretório para arquivos temporários (opcional)
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        
    def _generate_safe_filename(self, extension: str) -> str:
        """
        Gera um nome de arquivo seguro e único.
        
        Args:
            extension: Extensão do arquivo (sem ponto)
            
        Returns:
            Nome de arquivo único
        """
        return f"{uuid.uuid4().hex}.{extension}"
    
    def _validate_pdf_content(self, content: bytes) -> bool:
        """
        Valida se o conteúdo é realmente um PDF.
        
        Args:
            content: Bytes do arquivo
            
        Returns:
            True se for um PDF válido
        """
        if len(content) < 4:
            return False
        return content[:4] == self.PDF_MAGIC_BYTES
    
    async def convert_from_bytes(self, pdf_content: bytes) -> bytes:
        """
        Converte PDF de bytes para DOCX.
        
        Args:
            pdf_content: Conteúdo do PDF em bytes
            
        Returns:
            Conteúdo do DOCX em bytes
            
        Raises:
            PDFConverterError: Se a conversão falhar
        """
        # Valida o conteúdo do PDF
        if not self._validate_pdf_content(pdf_content):
            raise PDFConverterError("Arquivo não é um PDF válido")
        
        # Cria arquivos temporários com nomes seguros
        pdf_filename = self._generate_safe_filename("pdf")
        docx_filename = self._generate_safe_filename("docx")
        
        pdf_path = Path(self.temp_dir) / pdf_filename
        docx_path = Path(self.temp_dir) / docx_filename
        
        try:
            # Escreve o PDF temporário
            pdf_path.write_bytes(pdf_content)
            
            # Realiza a conversão
            logger.info(f"Iniciando conversão: {pdf_filename} -> {docx_filename}")
            
            cv = Converter(str(pdf_path))
            # Parâmetros ajustados para PDFs gerados de HTML (ex: Gotenberg)
            # Aumenta tolerância para linhas desenhadas via CSS que podem não se tocar perfeitamente
            cv.convert(str(docx_path), start=0, end=None,
                       min_line_len=1,           # Detecta linhas curtas
                       intersection_tolerance=10, # Tolerância para cruzamento de linhas
                       join_tolerance=10,         # Tolerância para unir segmentos próximos
                       snap_tolerance=4          # Tolerância para alinhamento (snap)
            )
            cv.close()
            
            # Lê o DOCX resultante
            if not docx_path.exists():
                raise PDFConverterError("Falha na conversão: arquivo DOCX não foi gerado")
            
            docx_content = docx_path.read_bytes()
            
            logger.info(f"Conversão concluída com sucesso: {len(docx_content)} bytes")
            
            return docx_content
            
        except PDFConverterError:
            raise
        except Exception as e:
            logger.error(f"Erro na conversão: {str(e)}")
            raise PDFConverterError(f"Erro durante a conversão: {str(e)}")
        finally:
            # Limpa arquivos temporários de forma segura
            self._safe_delete(pdf_path)
            self._safe_delete(docx_path)
    
    def _safe_delete(self, path: Path) -> None:
        """
        Remove arquivo de forma segura, ignorando erros.
        
        Args:
            path: Caminho do arquivo
        """
        try:
            if path.exists():
                path.unlink()
                logger.debug(f"Arquivo temporário removido: {path}")
        except Exception as e:
            logger.warning(f"Não foi possível remover arquivo temporário {path}: {e}")


# Instância global do conversor
converter = PDFToDocxConverter()
