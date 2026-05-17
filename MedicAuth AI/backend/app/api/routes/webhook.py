"""
Webhook para recibir eventos de Notion
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import re
import time

from app.services.notion_service import notion_service
from app.services.ai_agent import ai_agent
from app.utils.validators import validar_solicitud_completa

router = APIRouter()


# ------------------------------------------------------------------
# Extracción de page_id
# ------------------------------------------------------------------

def _extract_page_id(payload: Dict[str, Any]) -> Optional[str]:
    """
    Extrae el page_id real desde el payload del webhook.
    Soporta: campo directo, URL de Notion, o entity_id de automatización.
    """

    def normalize(raw_id: str) -> str:
        return raw_id.replace("-", "").strip()

    def is_valid_id(clean: str) -> bool:
        return len(clean) == 32 and all(c in "0123456789abcdef" for c in clean)

    def extract_from_url(url: str) -> Optional[str]:
        """Toma el ID del PATH de la URL, ignorando el ?v= (view ID)"""
        path = urlparse(url).path
        matches = re.findall(r'[0-9a-f]{32}', path.replace("-", ""))
        return matches[-1] if matches else None

    # 1. Campos directos más comunes
    for key in ("page_id", "id", "entity_id"):
        val = payload.get(key)
        if val and isinstance(val, str):
            if "notion.so" in val:
                extracted = extract_from_url(val)
                if extracted:
                    return extracted
            clean = normalize(val)
            if is_valid_id(clean):
                return clean

    # 2. Payload de automatización nativa de Notion
    data = payload.get("data", {})
    if isinstance(data, dict):
        obj_id = data.get("id") or data.get("page_id")
        if obj_id:
            clean = normalize(obj_id)
            if is_valid_id(clean):
                return clean

    # 3. Búsqueda genérica: cualquier clave con "page" que tenga un ID válido
    for key, val in payload.items():
        if "page" in key.lower() and isinstance(val, str):
            clean = normalize(val)
            if is_valid_id(clean):
                return clean

    return None


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/notion")
async def handle_notion_webhook(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """
    Recibe webhook de Notion cuando se crea/actualiza una solicitud.

    Flujo:
    1. Extrae page_id del payload (soporta IDs directos y URLs completas)
    2. Procesa en background: valida → busca póliza → analiza con IA → actualiza Notion
    """
    try:
        print(f"📨 Webhook recibido de Notion")

        page_id = _extract_page_id(payload)
        if not page_id:
            raise HTTPException(status_code=400, detail="page_id no encontrado en payload")

        background_tasks.add_task(process_authorization_request, page_id)

        return {
            "status": "accepted",
            "message": f"Solicitud {page_id[:8]}... en procesamiento",
            "page_id": page_id
        }

    except Exception as e:
        print(f"❌ Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notion/from-url")
async def trigger_from_notion_url(
    body: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """
    Dispara el procesamiento pasando directamente la URL de Notion.
    Body: {"url": "https://www.notion.so/REQ-002-362e23da..."}
    """
    url = body.get("url", "")
    if not url:
        raise HTTPException(status_code=400, detail="Campo 'url' requerido")

    page_id = _extract_page_id({"page_id": url})
    if not page_id:
        raise HTTPException(status_code=400, detail=f"No se pudo extraer page_id de: {url}")

    background_tasks.add_task(process_authorization_request, page_id)

    return {
        "status": "accepted",
        "page_id": page_id,
        "message": f"Procesando {page_id[:8]}..."
    }


@router.get("/test")
async def test_webhook():
    return {
        "status": "ok",
        "message": "Webhook funcionando",
        "notion_configured": bool(notion_service.solicitudes_db_id)
    }


# ------------------------------------------------------------------
# Procesamiento principal
# ------------------------------------------------------------------

async def process_authorization_request(page_id: str):
    """Procesa una solicitud de autorización completa"""
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

        # 3. ── VALIDACIÓN ROBUSTA ──────────────────────────────────────
        validacion = validar_solicitud_completa(solicitud)

        if validacion.advertencias:
            for adv in validacion.advertencias:
                print(f"⚠️  {adv}")

        if not validacion.valido:
            print(f"❌ Validación fallida: {validacion.errores}")
            await notion_service.update_authorization_status(
                page_id=page_id,
                status="Documentos Faltantes",
                decision={"error": "Validación de campos fallida", "detalle": validacion.errores},
                reasoning=(
                    "La solicitud no pasó la validación automática de campos:\n"
                    + "\n".join(f"  • {e}" for e in validacion.errores)
                ),
                confidence=100,
                missing_docs=validacion.campos_faltantes_formateados,
                processing_time=time.time() - start_time
            )
            return
        # ─────────────────────────────────────────────────────────────

        # 4. Buscar póliza
        # numero_poliza puede ser el page_id UUID de la relación;
        # get_policy_by_number maneja ambos casos (título o UUID directo)
        poliza_page = await notion_service.get_policy_by_number(solicitud.numero_poliza)
        if not poliza_page:
            print(f"❌ Póliza no encontrada: {solicitud.numero_poliza}")
            await notion_service.update_authorization_status(
                page_id=page_id,
                status="Documentos Faltantes",
                decision={"error": "Póliza no encontrada"},
                reasoning=f"No se encontró la póliza '{solicitud.numero_poliza}' en el sistema.",
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

        # 5. Verificar que la póliza esté activa
        if poliza.estado.lower() != "activa":
            await notion_service.update_authorization_status(
                page_id=page_id,
                status="Rechazado",
                decision={"error": f"Póliza en estado: {poliza.estado}"},
                reasoning=f"La póliza {poliza.numero_poliza} no está activa (estado actual: {poliza.estado}).",
                confidence=100,
                missing_docs=[],
                processing_time=time.time() - start_time
            )
            return

        # 6. Extraer texto del informe médico PDF (si existe)
        informe_medico_text = None
        if solicitud.informe_medico_url:
            from app.utils.pdf_extractor import pdf_extractor
            raw_text = await pdf_extractor.extract_text_from_url(solicitud.informe_medico_url)
            if raw_text:
                informe_medico_text = pdf_extractor.summarize_long_text(raw_text, max_chars=3000)
                print(f"📎 Informe médico extraído: {len(informe_medico_text)} caracteres")
            else:
                print(f"⚠️  No se pudo extraer texto del informe médico")
        else:
            print(f"ℹ️  Solicitud sin informe médico adjunto")

        # 7. Procesar con IA
        print(f"🤖 Enviando a agente IA...")
        decision = await ai_agent.process_authorization(
            solicitud=solicitud,
            poliza=poliza,
            informe_medico_text=informe_medico_text
        )

        print(f"{'✅' if decision.aprobado else '❌'} Decisión: {'APROBADO' if decision.aprobado else 'RECHAZADO'}")
        print(f"📊 Confianza: {decision.score_confianza}%")

        # 8. Determinar estado final
        if decision.aprobado:
            status = "Aprobado"
        elif decision.documentos_faltantes:
            status = "Documentos Faltantes"
        else:
            status = "Rechazado"

        # 9. Actualizar Notion
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
        except Exception:
            pass