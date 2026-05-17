"""
Servicio para integración con Notion API
"""

from notion_client import AsyncClient  # ← AsyncClient, no Client
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from app.core.config import settings
from app.models.authorization import SolicitudAutorizacion, Poliza, EstadoSolicitud

class NotionService:
    """Cliente para interactuar con Notion"""

    def __init__(self):
        self.client = AsyncClient(auth=settings.NOTION_TOKEN)  # ← async
        self.solicitudes_db_id = settings.NOTION_SOLICITUDES_DB_ID
        self.polizas_db_id = settings.NOTION_POLIZAS_DB_ID

    def _extract_text(self, property_obj: Dict[str, Any], key: str = "rich_text") -> str:
        """Helper seguro para extraer texto de arrays title o rich_text"""
        text_list = property_obj.get(key, []) if property_obj else []
        if text_list and isinstance(text_list, list):
            return text_list[0].get("text", {}).get("content", "")
        return ""

    def _build_status_filter(self, status: str) -> Dict[str, Any]:
        """Construye el filtro de estado reutilizable"""
        return {
            "property": "Estado",
            "select": {"equals": status}
        }

    async def get_pending_authorizations(self) -> List[Dict[str, Any]]:
        """Obtiene todas las solicitudes pendientes"""
        return await self.query_authorizations_by_status("Pendiente")

    async def query_authorizations_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Obtiene solicitudes filtradas por estado — soporta paginación automática"""
        try:
            results = []
            cursor = None

            while True:
                kwargs = {
                    "database_id": self.solicitudes_db_id,
                    "filter": self._build_status_filter(status),
                    "page_size": 100,
                }
                if cursor:
                    kwargs["start_cursor"] = cursor

                response = await self.client.databases.query(**kwargs)
                results.extend(response.get("results", []))

                if not response.get("has_more"):
                    break
                cursor = response.get("next_cursor")

            return results
        except Exception as e:
            print(f"❌ Error consultando solicitudes [{status}]: {e}")
            return []

    async def get_authorization_by_id(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una solicitud específica por ID"""
        try:
            return await self.client.pages.retrieve(page_id=page_id)
        except Exception as e:
            print(f"❌ Error obteniendo solicitud {page_id}: {e}")
            return None

    async def get_policy_by_number(self, policy_number: str) -> Optional[Dict[str, Any]]:
        """Busca una póliza por número"""
        try:
            response = await self.client.databases.query(
                database_id=self.polizas_db_id,
                filter={
                    "property": "Número Póliza",
                    "title": {"equals": policy_number}
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
                "Estado": {"select": {"name": status}},
                "Razonamiento": {
                    "rich_text": [{"text": {"content": reasoning[:2000]}}]
                },
                "Score Confianza": {"number": round(confidence, 2)},
                "Fecha Respuesta": {"date": {"start": datetime.now().isoformat()}},
                "Tiempo Procesamiento": {"number": round(processing_time, 2)},
            }

            if decision:
                properties["Decisión IA"] = {
                    "rich_text": [
                        {"text": {"content": json.dumps(decision, ensure_ascii=False)[:2000]}}
                    ]
                }

            if missing_docs:
                properties["Documentos Faltantes"] = {
                    "multi_select": [{"name": doc} for doc in missing_docs[:10]]
                }

            await self.client.pages.update(page_id=page_id, properties=properties)
            print(f"✅ Solicitud {page_id[:8]}... actualizada: {status}")
            return True

        except Exception as e:
            print(f"❌ Error actualizando solicitud {page_id}: {e}")
            return False

    def parse_notion_page_to_solicitud(self, page: Dict[str, Any]) -> Optional[SolicitudAutorizacion]:
        """Convierte una página de Notion a SolicitudAutorizacion"""
        try:
            props = page.get("properties", {})

            id_title_list = props.get("ID Solicitud", {}).get("title", [])
            id_text = id_title_list[0].get("text", {}).get("content", "") if id_title_list else ""

            paciente_nombre = self._extract_text(props.get("Paciente Nombre"))
            cedula = self._extract_text(props.get("Cédula"))
            medico = self._extract_text(props.get("Médico Tratante"))

            hospital = ((props.get("Hospital") or {}).get("select") or {}).get("name", "")
            tipo_cirugia = (props.get("Tipo Cirugía", {}) or {}).get("select", {}).get("name", "")
            estado = (props.get("Estado", {}) or {}).get("select", {}).get("name", "Pendiente")
            edad = (props.get("Edad") or {}).get("number", 0)

            poliza_relation = (props.get("Número Póliza") or {}).get("relation", [])
            numero_poliza = poliza_relation[0].get("id", "") if poliza_relation else ""

            fecha_sol = (props.get("Fecha Solicitada") or {}).get("date") or {}
            fecha_solicitada = fecha_sol.get("start", datetime.now().isoformat())

            files = (props.get("Informe Médico") or {}).get("files", [])
            informe_url = files[0].get("file", {}).get("url") if files and "file" in files[0] else None

            return SolicitudAutorizacion(
                id_solicitud=page.get("id", ""),
                paciente_nombre=paciente_nombre,
                cedula=cedula,
                edad=edad,
                numero_poliza=numero_poliza,
                tipo_cirugia=tipo_cirugia,
                fecha_solicitada=datetime.fromisoformat(fecha_solicitada.replace("Z", "+00:00")),
                hospital=hospital,
                medico_tratante=medico,
                informe_medico_url=informe_url,
                estado=estado,
            )
        except Exception as e:
            print(f"❌ Error parseando página de Notion: {e}")
            return None

    def parse_notion_page_to_poliza(self, page: Dict[str, Any]) -> Optional[Poliza]:
        """Convierte una página de Notion a Poliza"""
        try:
            props = page.get("properties", {})

            num_poliza_list = (props.get("Número Póliza") or {}).get("title", [])
            numero_poliza = num_poliza_list[0].get("text", {}).get("content", "") if num_poliza_list else ""

            aseguradora = (props.get("Aseguradora") or {}).get("select", {}).get("name", "")
            tipo_plan = (props.get("Tipo Plan") or {}).get("select", {}).get("name", "Básico")
            estado = (props.get("Estado") or {}).get("select", {}).get("name", "Activa")
            titular = self._extract_text(props.get("Titular"))
            carencia_dias = (props.get("Carencia Días") or {}).get("number", 0)

            coberturas_text = self._extract_text(props.get("Coberturas"))
            try:
                coberturas = json.loads(coberturas_text) if coberturas_text else {}
            except json.JSONDecodeError:
                coberturas = {}

            exclusiones_text = self._extract_text(props.get("Exclusiones"))
            exclusiones = [e.strip() for e in exclusiones_text.split(",") if e.strip()]

            fecha_inicio = ((props.get("Fecha Inicio") or {}).get("date") or {}).get("start", datetime.now().isoformat())
            fecha_fin = ((props.get("Fecha Fin") or {}).get("date") or {}).get("start", datetime.now().isoformat())

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
                estado=estado,
            )
        except Exception as e:
            print(f"❌ Error parseando póliza de Notion: {e}")
            return None


# Singleton
notion_service = NotionService()