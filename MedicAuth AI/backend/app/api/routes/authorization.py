"""
Rutas para gestión de autorizaciones
"""

from fastapi import APIRouter, HTTPException
from typing import List
from app.services.notion_service import notion_service

router = APIRouter()

@router.get("/pending")
async def get_pending_authorizations():
    """
    Obtiene todas las solicitudes pendientes
    """
    try:
        results = await notion_service.get_pending_authorizations()
        
        # Parsear a modelos
        solicitudes = []
        for page in results:
            solicitud = notion_service.parse_notion_page_to_solicitud(page)
            if solicitud:
                solicitudes.append(solicitud.model_dump())
        
        return {
            "count": len(solicitudes),
            "solicitudes": solicitudes
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{page_id}")
async def get_authorization_details(page_id: str):
    """
    Obtiene detalles de una solicitud específica
    """
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

@router.get("/stats/summary")
async def get_authorization_stats():
    """
    Obtiene estadísticas de autorizaciones
    """
    try:
        # TODO: Implementar queries para obtener stats reales
        return {
            "total_solicitudes": 0,
            "aprobadas": 0,
            "rechazadas": 0,
            "pendientes": 0,
            "docs_faltantes": 0,
            "tiempo_promedio": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
