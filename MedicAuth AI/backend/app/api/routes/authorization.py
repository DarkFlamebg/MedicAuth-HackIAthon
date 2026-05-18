from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File
import cloudinary
import cloudinary.uploader
from typing import List
import json
import re
import httpx
import tempfile
import pathlib
import time
from app.models.authorization import SolicitudCreate
from app.services.notion_service import notion_service
from app.core.dependencies import rate_limiter_in_memory

router = APIRouter(
    dependencies=[Depends(rate_limiter_in_memory(times=7, seconds=1))]
)


async def analizar_pdf_con_gemini(pdf_url: str, nombre_archivo: str) -> dict:
    """Lee PDF desde URL y extrae información médica con Gemini"""
    import google.generativeai as genai
    from app.core.config import settings

    genai.configure(api_key=settings.GEMINI_API_KEY)

    async with httpx.AsyncClient() as client:
        response = await client.get(pdf_url, timeout=30)
        pdf_bytes = response.content

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    archivo_gemini = genai.upload_file(
        path=tmp_path,
        display_name=nombre_archivo,
        mime_type="application/pdf",
    )

    pathlib.Path(tmp_path).unlink(missing_ok=True)

    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = """
    Analiza este informe médico PDF y extrae en JSON:
    {
        "paciente_nombre": "nombre completo",
        "cedula": "identificación",
        "edad": null o número,
        "diagnostico": "diagnóstico principal",
        "tipo_cirugia": "tipo de cirugía",
        "medico_tratante": "médico",
        "hospital": "hospital/clínica",
        "fecha_solicitada": "YYYY-MM-DD",
        "observaciones": "observaciones",
        "documentos_presentes": ["lista de documentos"],
        "resumen": "resumen 2-3 oraciones"
    }
    Responde ÚNICAMENTE con JSON válido, sin markdown.
    """

    resultado = model.generate_content([archivo_gemini, prompt])
    texto = resultado.text.strip()
    texto = re.sub(r"```json|```", "", texto).strip()

    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return {"resumen": texto, "error": "No se pudo parsear JSON completo"}

@router.get("/pending")
async def get_pending_authorizations():
    """Obtiene todas las solicitudes pendientes"""
    try:
        results = await notion_service.get_pending_authorizations()
        solicitudes = []
        for page in results:
            solicitud = notion_service.parse_notion_page_to_solicitud(page)
            if solicitud:
                solicitudes.append(solicitud.model_dump())
        return {"count": len(solicitudes), "solicitudes": solicitudes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_authorization_stats():
    """Obtiene estadísticas reales de autorizaciones desde Notion"""
    try:
        # Queries en paralelo por estado
        import asyncio

        results = await asyncio.gather(
            notion_service.query_authorizations_by_status("Pendiente"),
            notion_service.query_authorizations_by_status("Aprobado"),
            notion_service.query_authorizations_by_status("Rechazado"),
            notion_service.query_authorizations_by_status("Documentos Faltantes"),
            return_exceptions=True
        )

        pendientes_pages, aprobadas_pages, rechazadas_pages, docs_pages = [
            r if not isinstance(r, Exception) else []
            for r in results
        ]

        # Calcular tiempo promedio de procesamiento (en segundos)
        # Asume que la póliza tiene un campo "Tiempo Procesamiento" (número en segundos)
        all_processed = aprobadas_pages + rechazadas_pages + docs_pages
        tiempos = []
        for page in all_processed:
            props = page.get("properties", {})
            tiempo_prop = props.get("Tiempo Procesamiento", {})
            valor = tiempo_prop.get("number")
            if valor is not None:
                tiempos.append(valor)

        tiempo_promedio = round(sum(tiempos) / len(tiempos), 2) if tiempos else 0

        total = (
            len(pendientes_pages)
            + len(aprobadas_pages)
            + len(rechazadas_pages)
            + len(docs_pages)
        )

        return {
            "total_solicitudes": total,
            "aprobadas": len(aprobadas_pages),
            "rechazadas": len(rechazadas_pages),
            "pendientes": len(pendientes_pages),
            "docs_faltantes": len(docs_pages),
            "tiempo_promedio_segundos": tiempo_promedio,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-pdf", status_code=200)
async def upload_pdf(file: UploadFile = File(...)):
    """Sube PDF a Cloudinary, Gemini lo analiza, retorna URL + análisis"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un documento PDF")

    try:
        result = cloudinary.uploader.upload(
            file.file,
            resource_type="raw",
            folder="medicauth_pdfs",
            public_id=f"{file.filename.replace('.pdf', '')}_{int(time.time())}",
            overwrite=False,
        )
        pdf_url = result.get("secure_url")
        print(f"[CLOUDINARY] PDF subido: {pdf_url}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error subiendo a Cloudinary: {str(e)}")

    try:
        analisis = await analizar_pdf_con_gemini(pdf_url, file.filename)
        print(f"[GEMINI] Análisis completado")
    except Exception as e:
        print(f"[WARNING] Gemini no pudo analizar el PDF: {e}")
        analisis = {}

    return {
        "status": "success",
        "url": pdf_url,
        "analisis": analisis,
        "mensaje": "PDF subido y analizado correctamente"
    }


@router.post("/create", status_code=201)
async def create_authorization(
    solicitud: SolicitudCreate, 
    background_tasks: BackgroundTasks
):
    """Crea una nueva solicitud en Notion y dispara el análisis IA"""
    try:
        page_id = await notion_service.create_authorization_request(solicitud)
        
        if not page_id:
            raise HTTPException(status_code=500, detail="No se pudo crear la solicitud en Notion")
            
        # Importar aquí para evitar referencias circulares si webhook depende de algo más
        from app.api.routes.webhook import process_authorization_request
        
        # Encolar el procesamiento de IA
        background_tasks.add_task(process_authorization_request, page_id)
        
        return {
            "status": "success", 
            "message": "Solicitud creada y enviada a análisis", 
            "page_id": page_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{page_id}")
async def get_authorization_details(page_id: str):
    """Obtiene detalles de una solicitud específica"""
    try:
        page = await notion_service.get_authorization_by_id(page_id)
        if not page:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        solicitud = notion_service.parse_notion_page_to_solicitud(page)
        if not solicitud:
            raise HTTPException(status_code=500, detail="Error parseando solicitud")
        return solicitud.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))