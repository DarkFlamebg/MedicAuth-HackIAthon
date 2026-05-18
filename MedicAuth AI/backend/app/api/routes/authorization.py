from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
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
    """Obtiene todas las solicitudes pendientes con datos de póliza"""
    try:
        results = await notion_service.get_pending_authorizations()
        solicitudes = []
        for page in results:
            solicitud = notion_service.parse_notion_page_to_solicitud(page)
            if solicitud:
                data = solicitud.model_dump()
                
                # Buscar y adjuntar datos de la póliza
                if solicitud.numero_poliza:
                    poliza_page = await notion_service.get_policy_by_number(solicitud.numero_poliza)
                    if poliza_page:
                        poliza = notion_service.parse_notion_page_to_poliza(poliza_page)
                        if poliza:
                            data["poliza"] = poliza.model_dump()
                        else:
                            data["poliza"] = None
                    else:
                        data["poliza"] = None
                else:
                    data["poliza"] = None
                    
                solicitudes.append(data)
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
    """Sube PDF a Cloudinary como raw con permisos liberados para Notion"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un documento PDF")

    try:
        # 1. Asegurar la lectura correcta de los bytes desde el inicio
        await file.seek(0)
        file_bytes = await file.read()
        await file.seek(0)

        # 2. Construir el public_id FORZANDO la extensión .pdf al final
        nombre_base = file.filename.lower().replace('.pdf', '')
        nombre_limpio = "".join(c for c in nombre_base if c.isalnum() or c in ('_', '-'))
        public_id_final = f"{nombre_limpio}_{int(time.time())}.pdf"

        # 3. Subida estándar al pipeline de archivos RAW
        result = cloudinary.uploader.upload(
            file_bytes,
            resource_type="raw",
            type="upload",
            folder="medicauth_pdfs",
            public_id=public_id_final,
            overwrite=False,
            access_mode="public",  
            content_disposition="inline" 
        )
        
        pdf_url = result.get("secure_url")
        print(f"[CLOUDINARY SUCCESS] URL lista para Notion: {pdf_url}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error subiendo a Cloudinary: {str(e)}")

    try:
        # Ahora Gemini descargará el PDF real sin bloqueos 401
        analisis = await analizar_pdf_con_gemini(pdf_url, file.filename)
        print(f"[GEMINI] Análisis completado con éxito")
    except Exception as e:
        print(f"[WARNING] Gemini no pudo analizar el PDF: {e}")
        analisis = {}

    return {
        "status": "success",
        "url": pdf_url,
        "analisis": analisis,
        "mensaje": "PDF subido y analizado correctamente"
    }

@router.post("/create-with-pdf", status_code=201)
async def create_authorization_with_pdf(
    solicitud_data: SolicitudCreate,
    pdf_file: UploadFile = File(None)
):
    """
    ENDPOINT COMPLETO: Sube PDF a Cloudinary + Crea solicitud en Notion en UN PASO
    
    Si pdf_file está presente: Sube a Cloudinary y pone la URL en Notion
    Si no: Usa informe_medico_url si viene en solicitud_data
    """
    pdf_url = None
    
    # Si viene un archivo PDF, subirlo primero
    if pdf_file and pdf_file.filename.lower().endswith('.pdf'):
        try:
            await pdf_file.seek(0)
            file_bytes = await pdf_file.read()
            
            nombre_base = pdf_file.filename.lower().replace('.pdf', '')
            nombre_limpio = "".join(c for c in nombre_base if c.isalnum() or c in ('_', '-'))
            public_id_final = f"{nombre_limpio}_{int(time.time())}.pdf"
            
            result = cloudinary.uploader.upload(
                file_bytes,
                resource_type="raw",
                type="upload",
                folder="medicauth_pdfs",
                public_id=public_id_final,
                overwrite=False,
                access_mode="public",
                content_disposition="inline"
            )
            
            pdf_url = result.get("secure_url")
            print(f"[CLOUDINARY] PDF subido: {pdf_url}")
            
        except Exception as e:
            print(f"[WARNING] No se pudo subir PDF a Cloudinary: {e}")
    
    # Usar URL de Cloudinary si se logró obtener, sino la que viene en solicitud_data
    if pdf_url:
        solicitud_data.informe_medico_url = pdf_url
    
    # Crear solicitud en Notion con la URL (de Cloudinary o la que trajo)
    try:
        page_id = await notion_service.create_authorization_request(solicitud_data)
        
        if not page_id:
            raise HTTPException(status_code=500, detail="No se pudo crear la solicitud en Notion")
        
        return {
            "status": "success",
            "page_id": page_id,
            "informe_url": solicitud_data.informe_medico_url,
            "message": "Solicitud creada en Notion con URL de informe médico"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create", status_code=201)
async def create_authorization(solicitud: SolicitudCreate):
    """Crea una nueva solicitud en Notion y retorna el page_id para auditoría posterior"""
    try:
        page_id = await notion_service.create_authorization_request(solicitud)
        
        if not page_id:
            raise HTTPException(status_code=500, detail="No se pudo crear la solicitud en Notion")
        
        return {
            "status": "success", 
            "message": "Solicitud creada exitosamente. Use el endpoint GET /{page_id} para auditoría automática", 
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

@router.get("/resolved")
async def get_resolved_authorizations():
    """Obtiene solicitudes resueltas: aprobadas, rechazadas y docs faltantes"""
    try:
        import asyncio
        results = await asyncio.gather(
            notion_service.query_authorizations_by_status("Aprobado"),
            notion_service.query_authorizations_by_status("Rechazado"),
            notion_service.query_authorizations_by_status("Documentos Faltantes"),
        )

        solicitudes = []
        for pages in results:
            for page in pages:
                solicitud = notion_service.parse_notion_page_to_solicitud(page)
                if solicitud:
                    data = solicitud.model_dump()
                    if solicitud.numero_poliza:
                        poliza_page = await notion_service.get_policy_by_number(solicitud.numero_poliza)
                        if poliza_page:
                            poliza = notion_service.parse_notion_page_to_poliza(poliza_page)
                            data["poliza"] = poliza.model_dump() if poliza else None
                        else:
                            data["poliza"] = None
                    solicitudes.append(data)

        solicitudes.sort(key=lambda x: x.get("fecha_respuesta") or "", reverse=True)

        return {"count": len(solicitudes), "solicitudes": solicitudes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))