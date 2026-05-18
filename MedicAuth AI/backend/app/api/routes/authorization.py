from fastapi import APIRouter, HTTPException, Depends
from typing import List
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