#!/usr/bin/env python3
"""Test rápido del flujo Cloudinary + Gemini"""
import httpx
import asyncio
from pathlib import Path

async def test_upload_pdf():
    # Crear un PDF de prueba simple
    pdf_path = Path("test.pdf")

    # Si no existe, descargamos uno o creamos con reportlab
    if not pdf_path.exists():
        print("  Descargando PDF de prueba...")
        # Puedes usar cualquier PDF pequeño
        # Para esta prueba, vamos a asumir que tienes un PDF
        print(" Por favor, coloca un archivo 'test.pdf' en el directorio actual")
        return

    async with httpx.AsyncClient() as client:
        with open(pdf_path, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            try:
                print("📤 Subiendo PDF a Cloudinary...")
                response = await client.post(
                    "http://localhost:8000/api/authorization/upload-pdf",
                    files=files,
                    timeout=60
                )
                print(f"Status: {response.status_code}")
                print(f"Response: {response.json()}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"\n URL Cloudinary: {data.get('url')}")
                    print(f" Análisis Gemini: {data.get('analisis')}")
            except Exception as e:
                print(f" Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_upload_pdf())
