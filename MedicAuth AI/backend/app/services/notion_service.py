"""
Servicio para integración con Notion API
"""

from notion_client import AsyncClient
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from app.core.config import settings
from app.models.authorization import SolicitudAutorizacion, Poliza


def _get_rich_text(prop: dict) -> str:
    """Extrae texto enriquecido de forma segura, incluso si está vacío"""
    arr = prop.get("rich_text", [])
    if arr and len(arr) > 0:
        return arr[0].get("text", {}).get("content", "")
    return ""

def _get_title(prop: dict) -> str:
    """Extrae el título de forma segura"""
    arr = prop.get("title", [])
    if arr and len(arr) > 0:
        return arr[0].get("text", {}).get("content", "")
    return ""


class NotionService:
    """Cliente para interactuar con Notion"""
    
    def __init__(self):
        # USAR ASYNCCLIENT PARA NO BLOQUEAR FASTAPI
        self.client = AsyncClient(auth=settings.NOTION_TOKEN)
        self.solicitudes_db_id = settings.NOTION_SOLICITUDES_DB_ID
        self.polizas_db_id = settings.NOTION_POLIZAS_DB_ID
    
    async def get_pending_authorizations(self) -> List[Dict[str, Any]]:
        """Obtiene todas las solicitudes pendientes"""
        try:
            response = await self.client.databases.query(
                database_id=self.solicitudes_db_id,
                filter={
                    "property": "Estado",
                    "select": {
                        "equals": "Pendiente"
                    }
                }
            )
            return response.get("results", [])
        except Exception as e:
            print(f"[ERROR] Error obteniendo solicitudes pendientes: {e}")
            return []
            
    async def query_authorizations_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Obtiene solicitudes filtradas por estado (Para estadísticas)"""
        try:
            response = await self.client.databases.query(
                database_id=self.solicitudes_db_id,
                filter={
                    "property": "Estado",
                    "select": {
                        "equals": status
                    }
                }
            )
            return response.get("results", [])
        except Exception as e:
            print(f"[ERROR] Error consultando por estado {status}: {e}")
            return []
    
    async def get_authorization_by_id(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una solicitud específica por ID"""
        try:
            page = await self.client.pages.retrieve(page_id=page_id)
            return page
        except Exception as e:
            print(f"[ERROR] Error obteniendo solicitud {page_id}: {e}")
            return None
    
    async def get_policy_by_number(self, policy_number: str) -> Optional[Dict[str, Any]]:
        """Busca una póliza por número o por ID de página directo"""
        if not policy_number:
            return None
            
        try:
            clean_id = policy_number.replace("-", "").strip()
            if len(clean_id) == 32 and all(c in "0123456789abcdef" for c in clean_id):
                try:
                    page = await self.client.pages.retrieve(page_id=policy_number)
                    return page
                except Exception as retrieve_err:
                    print(f"[WARNING] No se pudo recuperar póliza por ID ({policy_number}): {retrieve_err}")
            
            response = await self.client.databases.query(
                database_id=self.polizas_db_id,
                filter={
                    "property": "Número Póliza",
                    "title": {
                        "equals": policy_number
                    }
                }
            )
            results = response.get("results", [])
            return results[0] if results else None
        except Exception as e:
            print(f"[ERROR] Error buscando póliza {policy_number}: {e}")
            return None
    
    async def update_authorization_status(
        self,
        page_id: str,
        status: str,
        decision: Dict[str, Any],
        reasoning: str,
        confidence: float,
        missing_docs: List[str] = None,
        processing_time: float = 0
    ) -> bool:
        """Actualiza el estado de una solicitud con la decisión de la IA"""
        try:
            properties = {
                "Estado": {
                    "select": {
                        "name": status
                    }
                },
                "Razonamiento": {
                    "rich_text": [
                        {
                            "text": {
                                "content": reasoning[:1900]
                            }
                        }
                    ]
                },
                "Score Confianza": {
                    "number": round(confidence, 2)
                },
                "Fecha Respuesta": {
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                },
                "Tiempo Procesamiento": {
                    "number": round(processing_time, 2)
                }
            }
            
            if decision:
                properties["Decisión IA"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": json.dumps(decision, ensure_ascii=False)[:1900]
                            }
                        }
                    ]
                }
            
            if missing_docs:
                properties["Documentos Faltantes"] = {
                    "multi_select": [
                        {"name": doc.replace(",", " -")[:100]} for doc in missing_docs[:10]
                    ]
                }
            
            await self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            print(f"[SUCCESS] Solicitud {page_id[:8]}... actualizada: {status}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error actualizando solicitud {page_id}: {e}")
            return False
    
    def parse_notion_page_to_solicitud(self, page: Dict[str, Any]) -> Optional[SolicitudAutorizacion]:
        """Convierte una página de Notion a modelo SolicitudAutorizacion"""
        try:
            props = page.get("properties", {})
            id_solicitud = page.get("id", "")
            
            # Usando helpers seguros para evitar list index out of range
            paciente_nombre = _get_rich_text(props.get("Paciente Nombre", {}))
            cedula = _get_rich_text(props.get("Cédula", {}))
            medico = _get_rich_text(props.get("Médico Tratante", {}))
            
            hospital = props.get("Hospital", {}).get("select", {})
            hospital_name = hospital.get("name", "") if hospital else ""
            
            edad = props.get("Edad", {}).get("number")
            edad = edad if edad is not None else 0
            
            tipo_cirugia_prop = props.get("Tipo Cirugía", {}).get("select", {})
            tipo_cirugia = tipo_cirugia_prop.get("name", "") if tipo_cirugia_prop else ""
            
            estado_prop = props.get("Estado", {}).get("select", {})
            estado = estado_prop.get("name", "Pendiente") if estado_prop else "Pendiente"
            
            poliza_relation = props.get("Número Póliza", {}).get("relation", [])
            numero_poliza = poliza_relation[0].get("id", "") if poliza_relation else ""
            
            fecha_sol = props.get("Fecha Solicitada", {}).get("date", {})
            fecha_solicitada = fecha_sol.get("start", datetime.now().isoformat()) if fecha_sol else datetime.now().isoformat()
            
            files = props.get("Informe Médico", {}).get("files", [])
            informe_url = files[0].get("file", {}).get("url", "") if files else None
            
            return SolicitudAutorizacion(
                id_solicitud=id_solicitud,
                paciente_nombre=paciente_nombre,
                cedula=cedula,
                edad=edad,
                numero_poliza=numero_poliza,
                tipo_cirugia=tipo_cirugia,
                fecha_solicitada=datetime.fromisoformat(fecha_solicitada.replace("Z", "+00:00")),
                hospital=hospital_name,
                medico_tratante=medico,
                informe_medico_url=informe_url,
                estado=estado
            )
        except Exception as e:
            print(f"[ERROR] Error parseando página de Notion: {e}")
            return None
    
    def parse_notion_page_to_poliza(self, page: Dict[str, Any]) -> Optional[Poliza]:
        """Convierte una página de Notion a modelo Poliza"""
        try:
            props = page.get("properties", {})
            
            numero_poliza = _get_title(props.get("Número Póliza", {}))
            titular = _get_rich_text(props.get("Titular", {}))
            
            aseguradora_prop = props.get("Aseguradora", {}).get("select", {})
            aseguradora = aseguradora_prop.get("name", "") if aseguradora_prop else ""
            
            tipo_plan_prop = props.get("Tipo Plan", {}).get("select", {})
            tipo_plan = tipo_plan_prop.get("name", "Básico") if tipo_plan_prop else "Básico"
            
            estado_prop = props.get("Estado", {}).get("select", {})
            estado = estado_prop.get("name", "Activa") if estado_prop else "Activa"
            
            carencia_dias = props.get("Carencia Días", {}).get("number")
            carencia_dias = carencia_dias if carencia_dias is not None else 0
            
            coberturas_text = _get_rich_text(props.get("Coberturas", {}))
            try:
                coberturas = json.loads(coberturas_text) if coberturas_text else {}
            except:
                coberturas = {}
            
            exclusiones_text = _get_rich_text(props.get("Exclusiones", {}))
            exclusiones = [e.strip() for e in exclusiones_text.split(",") if e.strip()]
            
            fecha_inicio_obj = props.get("Fecha Inicio", {}).get("date", {})
            fecha_inicio = fecha_inicio_obj.get("start", datetime.now().isoformat()) if fecha_inicio_obj else datetime.now().isoformat()
            
            fecha_fin_obj = props.get("Fecha Fin", {}).get("date", {})
            fecha_fin = fecha_fin_obj.get("start", datetime.now().isoformat()) if fecha_fin_obj else datetime.now().isoformat()
            
            return Poliza(
                numero_poliza=numero_poliza,
                aseguradora=aseguradora,
                titular=titular,
                tipo_plan=tipo_plan,
                coberturas=coberturas,
                exclusiones=exclusiones,
                carencia_dias=carencia_dias,
                fecha_inicio=datetime.fromisoformat(fecha_inicio.replace("Z", "+00:00")),
                fecha_fin=datetime.fromisoformat(fecha_fin.replace("Z", "+00:00")),
                estado=estado
            )
        except Exception as e:
            print(f"[ERROR] Error parseando póliza de Notion: {e}")
            return None

notion_service = NotionService()