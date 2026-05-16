"""
Webhook para recibir eventos de Notion
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
import time

from app.models.authorization import WebhookNotionPayload
from app.services.notion_service import notion_service
from app.services.ai_agent import ai_agent

router = APIRouter()

@router.post("/notion")
async def handle_notion_webhook(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """
    Recibe webhook de Notion cuando se crea/actualiza una solicitud
    
    Flujo:
    1. Recibe evento de Notion
    2. Extrae información de la solicitud
    3. Busca póliza relacionada
    4. Procesa con el agente IA
    5. Actualiza Notion con la decisión
    """
    try:
        print(f"📨 Webhook recibido de Notion")
        
        # Extraer page_id del payload
        page_id = payload.get("page_id") or payload.get("id")
        
        if not page_id:
            raise HTTPException(status_code=400, detail="page_id no encontrado en payload")
        
        # Procesar en background para responder rápido
        background_tasks.add_task(process_authorization_request, page_id)
        
        return {
            "status": "accepted",
            "message": f"Solicitud {page_id[:8]}... en procesamiento",
            "page_id": page_id
        }
        
    except Exception as e:
        print(f"❌ Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_authorization_request(page_id: str):
    """
    Procesa una solicitud de autorización completa
    """
    start_time = time.time()
    
    try:
        print(f"🔄 Procesando solicitud {page_id[:8]}...")
        
        # 1. Obtener solicitud de Notion
        page_data = await notion_service.get_authorization_by_id(page_id)
        
        if not page_data:
            print(f"❌ No se encontró página {page_id}")
            return
        
        # 2. Parsear a modelo
        solicitud = notion_service.parse_notion_page_to_solicitud(page_data)
        
        if not solicitud:
            print(f"❌ Error parseando solicitud {page_id}")
            return
        
        print(f"📋 Solicitud: {solicitud.paciente_nombre} - {solicitud.tipo_cirugia}")
        
        # 3. Buscar póliza
        poliza_page = await notion_service.get_policy_by_number(solicitud.numero_poliza)
        
        if not poliza_page:
            # No se encontró póliza - marcar como documentos faltantes
            await notion_service.update_authorization_status(
                page_id=page_id,
                status="Documentos Faltantes",
                decision={"error": "Póliza no encontrada"},
                reasoning=f"No se encontró la póliza {solicitud.numero_poliza} en el sistema",
                confidence=100,
                missing_docs=[f"Validar número de póliza: {solicitud.numero_poliza}"],
                processing_time=time.time() - start_time
            )
            return
        
        poliza = notion_service.parse_notion_page_to_poliza(poliza_page)
        
        if not poliza:
            print(f"❌ Error parseando póliza")
            return
        
        print(f"📄 Póliza encontrada: {poliza.numero_poliza} - {poliza.tipo_plan}")
        
        # 4. Obtener informe médico (si existe)
        informe_medico_text = None
        if solicitud.informe_medico_url:
            # TODO: Descargar y extraer texto del PDF
            # Por ahora, usamos None
            informe_medico_text = "Informe médico disponible en archivo adjunto"
        
        # 5. Procesar con IA
        print(f"🤖 Enviando a agente IA...")
        decision = await ai_agent.process_authorization(
            solicitud=solicitud,
            poliza=poliza,
            informe_medico_text=informe_medico_text
        )
        
        print(f"{'✅' if decision.aprobado else '❌'} Decisión: {'APROBADO' if decision.aprobado else 'RECHAZADO'}")
        print(f"📊 Confianza: {decision.score_confianza}%")
        
        # 6. Determinar estado
        if decision.aprobado:
            status = "Aprobado"
        elif decision.documentos_faltantes:
            status = "Documentos Faltantes"
        else:
            status = "Rechazado"
        
        # 7. Actualizar Notion
        await notion_service.update_authorization_status(
            page_id=page_id,
            status=status,
            decision={
                "aprobado": decision.aprobado,
                "clausulas_relevantes": decision.clausulas_relevantes,
                "recomendaciones": decision.recomendaciones
            },
            reasoning=decision.razonamiento,
            confidence=decision.score_confianza,
            missing_docs=decision.documentos_faltantes,
            processing_time=decision.tiempo_procesamiento
        )
        
        total_time = time.time() - start_time
        print(f"⏱️  Procesamiento completado en {total_time:.2f}s")
        
    except Exception as e:
        print(f"❌ Error procesando solicitud {page_id}: {e}")
        # Intentar actualizar Notion con el error
        try:
            await notion_service.update_authorization_status(
                page_id=page_id,
                status="Rechazado",
                decision={"error": str(e)},
                reasoning=f"Error en procesamiento automático: {str(e)}",
                confidence=0,
                missing_docs=["Requiere revisión manual"],
                processing_time=time.time() - start_time
            )
        except:
            pass

@router.get("/test")
async def test_webhook():
    """Endpoint de prueba"""
    return {
        "status": "ok",
        "message": "Webhook funcionando",
        "notion_configured": bool(notion_service.solicitudes_db_id)
    }
