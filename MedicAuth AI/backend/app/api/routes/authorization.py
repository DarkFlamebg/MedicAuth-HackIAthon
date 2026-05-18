from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File
import cloudinary
import cloudinary.uploader
from typing import List
from app.models.authorization import SolicitudCreate
from app.services.notion_service import notion_service
from app.core.dependencies import rate_limiter_in_memory

router = APIRouter(
    dependencies=[Depends(rate_limiter_in_memory(times=7, seconds=1))]
)

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
    """Sube un archivo PDF a Cloudinary y devuelve la URL segura"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un documento PDF")
    
    try:
        # Cloudinary automáticamente lee CLOUDINARY_URL de .env
        result = cloudinary.uploader.upload(
            file.file,
            resource_type="raw", # raw es requerido para documentos no-imagen
            folder="medicauth_pdfs"
        )
        
        return {
            "status": "success",
            "url": result.get("secure_url")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error subiendo a Cloudinary: {str(e)}")


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