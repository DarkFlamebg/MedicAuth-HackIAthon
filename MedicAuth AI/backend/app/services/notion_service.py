"""
Servicio para integración con Notion API
"""

from notion_client import Client
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from app.core.config import settings
from app.models.authorization import SolicitudAutorizacion, Poliza, EstadoSolicitud

class NotionService:
    """Cliente para interactuar con Notion"""
    
    def __init__(self):
        self.client = Client(auth=settings.NOTION_TOKEN)
        self.solicitudes_db_id = settings.NOTION_SOLICITUDES_DB_ID
        self.polizas_db_id = settings.NOTION_POLIZAS_DB_ID
    
    async def get_pending_authorizations(self) -> List[Dict[str, Any]]:
        """Obtiene todas las solicitudes pendientes"""
        try:
            response = self.client.databases.query(
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
            print(f"❌ Error obteniendo solicitudes pendientes: {e}")
            return []
    
    async def get_authorization_by_id(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una solicitud específica por ID"""
        try:
            page = self.client.pages.retrieve(page_id=page_id)
            return page
        except Exception as e:
            print(f"❌ Error obteniendo solicitud {page_id}: {e}")
            return None
    
    async def get_policy_by_number(self, policy_number: str) -> Optional[Dict[str, Any]]:
        """Busca una póliza por número"""
        try:
            response = self.client.databases.query(
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
            print(f"❌ Error buscando póliza {policy_number}: {e}")
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
                                "content": reasoning[:2000]  # Notion tiene límite
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
            
            # Agregar decisión IA como JSON
            if decision:
                properties["Decisión IA"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": json.dumps(decision, ensure_ascii=False)[:2000]
                            }
                        }
                    ]
                }
            
            # Agregar documentos faltantes si existen
            if missing_docs:
                properties["Documentos Faltantes"] = {
                    "multi_select": [
                        {"name": doc} for doc in missing_docs[:10]  # Máximo 10
                    ]
                }
            
            self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            print(f"✅ Solicitud {page_id[:8]}... actualizada: {status}")
            return True
            
        except Exception as e:
            print(f"❌ Error actualizando solicitud {page_id}: {e}")
            return False
    
    def parse_notion_page_to_solicitud(self, page: Dict[str, Any]) -> Optional[SolicitudAutorizacion]:
        """Convierte una página de Notion a modelo SolicitudAutorizacion"""
        try:
            props = page.get("properties", {})
            
            # Extraer valores de las propiedades de Notion
            id_solicitud = page.get("id", "")
            
            # Title field
            titulo = props.get("ID Solicitud", {})
            id_text = titulo.get("title", [{}])[0].get("text", {}).get("content", "")
            
            # Text fields
            paciente_nombre = props.get("Paciente Nombre", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            cedula = props.get("Cédula", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            medico = props.get("Médico Tratante", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            hospital = props.get("Hospital", {}).get("select", {}).get("name", "")
            
            # Number fields
            edad = props.get("Edad", {}).get("number", 0)
            
            # Select fields
            tipo_cirugia = props.get("Tipo Cirugía", {}).get("select", {}).get("name", "")
            estado = props.get("Estado", {}).get("select", {}).get("name", "Pendiente")
            
            # Relation to Poliza
            poliza_relation = props.get("Número Póliza", {}).get("relation", [])
            numero_poliza = poliza_relation[0].get("id", "") if poliza_relation else ""
            
            # Date
            fecha_sol = props.get("Fecha Solicitada", {}).get("date", {})
            fecha_solicitada = fecha_sol.get("start", datetime.now().isoformat()) if fecha_sol else datetime.now().isoformat()
            
            # Files
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
                hospital=hospital,
                medico_tratante=medico,
                informe_medico_url=informe_url,
                estado=estado
            )
        except Exception as e:
            print(f"❌ Error parseando página de Notion: {e}")
            return None
    
    def parse_notion_page_to_poliza(self, page: Dict[str, Any]) -> Optional[Poliza]:
        """Convierte una página de Notion a modelo Poliza"""
        try:
            props = page.get("properties", {})
            
            # Extraer propiedades
            numero_poliza = props.get("Número Póliza", {}).get("title", [{}])[0].get("text", {}).get("content", "")
            aseguradora = props.get("Aseguradora", {}).get("select", {}).get("name", "")
            titular = props.get("Titular", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            tipo_plan = props.get("Tipo Plan", {}).get("select", {}).get("name", "Básico")
            estado = props.get("Estado", {}).get("select", {}).get("name", "Activa")
            carencia_dias = props.get("Carencia Días", {}).get("number", 0)
            
            # Coberturas (JSON text)
            coberturas_text = props.get("Coberturas", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "{}")
            try:
                coberturas = json.loads(coberturas_text)
            except:
                coberturas = {}
            
            # Exclusiones (text)
            exclusiones_text = props.get("Exclusiones", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            exclusiones = [e.strip() for e in exclusiones_text.split(",") if e.strip()]
            
            # Fechas
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
            print(f"❌ Error parseando póliza de Notion: {e}")
            return None

# Singleton
notion_service = NotionService()
