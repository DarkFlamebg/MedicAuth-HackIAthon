import httpx
from typing import Optional

class PDFExtractor:
    """Descarga archivos PDF para ser procesados nativamente por Gemini"""
    
    @staticmethod
    async def download_pdf_bytes(pdf_url: str) -> Optional[bytes]:
        """
        Descarga un PDF desde una URL y retorna sus bytes.
        """
        try:
            print(f"[INFO] Descargando PDF desde {pdf_url[:50]}...")

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(pdf_url)
                response.raise_for_status()

            pdf_bytes = response.content
            print(f"[SUCCESS] PDF descargado: {len(pdf_bytes) / 1024:.2f} KB")
            return pdf_bytes

        except Exception as e:
            print(f"[ERROR] Error descargando PDF: {e}")
            return None
    
    @staticmethod
    def read_local_pdf_bytes(file_path: str) -> Optional[bytes]:
        """
        Lee un archivo PDF local y retorna sus bytes.
        """
        try:
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()
            print(f"[SUCCESS] PDF local leido: {len(pdf_bytes) / 1024:.2f} KB")
            return pdf_bytes
            
        except Exception as e:
            print(f"[ERROR] Error leyendo PDF local: {e}")
            return None

# Singleton
pdf_extractor = PDFExtractor()