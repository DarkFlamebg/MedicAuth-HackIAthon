import httpx

import requests
from pypdf import PdfReader
from io import BytesIO
from typing import Optional

class PDFExtractor:
    """Extrae texto de archivos PDF"""
    
    @staticmethod
    async def extract_text_from_url(pdf_url: str) -> Optional[str]:
        try:
            print(f"📄 Descargando PDF desde {pdf_url[:50]}...")

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(pdf_url)
                response.raise_for_status()

            pdf_file = BytesIO(response.content)
            reader = PdfReader(pdf_file)

            text_parts = []
            total_pages = len(reader.pages)
            print(f"📖 Extrayendo texto de {total_pages} página(s)...")

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(f"--- Página {i+1} ---\n{page_text}")

            full_text = "\n\n".join(text_parts)
            print(f"✅ Texto extraído: {len(full_text)} caracteres")
            return full_text if full_text.strip() else None

        except Exception as e:
            print(f"❌ Error extrayendo PDF: {e}")
            return None
    
    @staticmethod
    def extract_text_from_file(file_path: str) -> Optional[str]:
        """
        Extrae texto de un archivo PDF local
        
        Args:
            file_path: Ruta al archivo PDF
            
        Returns:
            Texto extraído del PDF o None si hay error
        """
        try:
            reader = PdfReader(file_path)
            text_parts = []
            
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text.strip():
                    text_parts.append(f"--- Página {i+1} ---\n{page_text}")
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            print(f"❌ Error leyendo PDF local: {e}")
            return None
    
    @staticmethod
    def summarize_long_text(text: str, max_chars: int = 3000) -> str:
        """
        Trunca texto largo para enviar a la IA
        
        Args:
            text: Texto completo
            max_chars: Máximo de caracteres a retornar
            
        Returns:
            Texto truncado con indicador
        """
        if len(text) <= max_chars:
            return text
        
        # Tomar inicio y final
        half = max_chars // 2
        return (
            f"{text[:half]}\n\n"
            f"[... contenido truncado: {len(text) - max_chars} caracteres omitidos ...]\n\n"
            f"{text[-half:]}"
        )

# Singleton
pdf_extractor = PDFExtractor()