"""
Servicio para integración con Notion API
"""

from notion_client import AsyncClient
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from app.core.config import settings
from app.models.authorization import SolicitudAutorizacion, Poliza, EstadoSolicitud


class NotionService:
    """Cliente para interactuar con Notion"""

    def __init__(self):
        self.client = AsyncClient(auth=settings.NOTION_TOKEN)
        self.solicitudes_db_id = settings.NOTION_SOLICITUDES_DB_ID
        self.polizas_db_id = settings.NOTION_POLIZAS_DB_ID

    # ------------------------------------------------------------------
    # Helpers de extracción
    # ------------------------------------------------------------------

    def _extract_text(self, property_obj: Dict[str, Any], key: str = "rich_text") -> str:
        """Extrae texto de rich_text o title de forma segura"""
        text_list = property_obj.get(key, []) if property_obj else []
        if text_list and isinstance(text_list, list):
            return text_list[0].get("text", {}).get("content", "")
        return ""

    def _extract_select(self, property_obj: Any, default: str = "") -> str:
        """Extrae el nombre de un campo select, manejando select: null"""
        return ((property_obj or {}).get("select") or {}).get("name", default)

    def _extract_date(self, property_obj: Any, default: Optional[str] = None) -> Optional[str]:
        """Extrae el start de un campo date, manejando date: null"""
        date_obj = (property_obj or {}).get("date")
        if date_obj:
            return date_obj.get("start")
        return default

    def _extract_number(self, property_obj: Any, default: int = 0) -> int:
        """Extrae un número de forma segura"""
        return (property_obj or {}).get("number") or default

    def _build_status_filter(self, status: str) -> Dict[str, Any]:
        return {"property": "Estado", "select": {"equals": status}}

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_pending_authorizations(self) -> List[Dict[str, Any]]:
        return await self.query_authorizations_by_status("Pendiente")

    async def query_authorizations_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Solicitudes por estado con paginación automática"""
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
        try:
            return await self.client.pages.retrieve(page_id=page_id)
        except Exception as e:
            print(f"❌ Error obteniendo solicitud {page_id}: {e}")
            return None

    async def get_policy_by_number(self, policy_number: str) -> Optional[Dict[str, Any]]:
        """
        Busca póliza por número de título.
        policy_number puede ser el título (POL-2026-TEST)
        o un page_id UUID si la relación solo trae el id.
        Intenta ambas estrategias.
        """
        if not policy_number:
            return None
        try:
            # Estrategia 1: buscar por título (caso normal)
            response = await self.client.databases.query(
                database_id=self.polizas_db_id,
                filter={"property": "Número Póliza", "title": {"equals": policy_number}}
            )
            results = response.get("results", [])
            if results:
                return results[0]

            # Estrategia 2: si no encontró por título, intentar por page_id directo
            # (ocurre cuando el campo Número Póliza es una relación y solo tenemos el UUID)
            if len(policy_number.replace("-", "")) == 32:
                print(f"⚠️  Buscando póliza por page_id directo: {policy_number[:8]}...")
                page = await self.client.pages.retrieve(page_id=policy_number)
                return page if page else None

            return None
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
                    "rich_text": [{"text": {"content": json.dumps(decision, ensure_ascii=False)[:2000]}}]
                }
            if missing_docs:
                properties["Documentos Faltantes"] = {
                    "multi_select": [{"name": doc[:99]} for doc in missing_docs[:10]]
                }
            await self.client.pages.update(page_id=page_id, properties=properties)
            print(f"✅ Solicitud {page_id[:8]}... actualizada: {status}")
            return True
        except Exception as e:
            print(f"❌ Error actualizando solicitud {page_id}: {e}")
            return False

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    def parse_notion_page_to_solicitud(self, page: Dict[str, Any]) -> Optional[SolicitudAutorizacion]:
        """Convierte una página de Notion a SolicitudAutorizacion"""
        try:
            props = page.get("properties", {})

            paciente_nombre = self._extract_text(props.get("Paciente Nombre"))
            cedula          = self._extract_text(props.get("Cédula"))
            medico          = self._extract_text(props.get("Médico Tratante"))
            hospital        = self._extract_select(props.get("Hospital"))
            tipo_cirugia    = self._extract_select(props.get("Tipo Cirugía"))
            estado          = self._extract_select(props.get("Estado"), default="Pendiente")
            edad            = self._extract_number(props.get("Edad"))

            # ── Número de póliza ──────────────────────────────────────────
            # La columna "Número Póliza" en Solicitudes es una RELACIÓN.
            # Notion devuelve solo el page_id de la póliza relacionada,
            # NO el texto del título. Guardamos el page_id y en el webhook
            # lo resolvemos con get_policy_by_number (estrategia 2).
            poliza_relation = (props.get("Número Póliza") or {}).get("relation", [])
            numero_poliza   = poliza_relation[0].get("id", "") if poliza_relation else ""
            # ──────────────────────────────────────────────────────────────

            fecha_inicio_raw = self._extract_date(
                props.get("Fecha Solicitada"),
                default=datetime.now().isoformat()
            )

            files       = (props.get("Informe Médico") or {}).get("files", [])
            informe_url = None
            if files:
                first = files[0]
                # Archivos subidos directamente a Notion
                if first.get("type") == "file":
                    informe_url = first.get("file", {}).get("url")
                # Archivos vinculados por URL externa
                elif first.get("type") == "external":
                    informe_url = first.get("external", {}).get("url")

            return SolicitudAutorizacion(
                id_solicitud=page.get("id", ""),
                paciente_nombre=paciente_nombre,
                cedula=cedula,
                edad=edad,
                numero_poliza=numero_poliza,
                tipo_cirugia=tipo_cirugia,
                fecha_solicitada=datetime.fromisoformat(
                    fecha_inicio_raw.replace("Z", "+00:00")
                ),
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

            numero_poliza = self._extract_text(props.get("Número Póliza"), key="title")
            aseguradora   = self._extract_select(props.get("Aseguradora"))
            tipo_plan     = self._extract_select(props.get("Tipo Plan"), default="Básico")
            estado        = self._extract_select(props.get("Estado"), default="Activa")
            titular       = self._extract_text(props.get("Titular"))
            carencia_dias = self._extract_number(props.get("Carencia Días"))

            coberturas_text = self._extract_text(props.get("Coberturas"))
            try:
                coberturas = json.loads(coberturas_text) if coberturas_text else {}
            except json.JSONDecodeError:
                coberturas = {}

            exclusiones_text = self._extract_text(props.get("Exclusiones"))
            exclusiones = [e.strip() for e in exclusiones_text.split(",") if e.strip()]

            fecha_inicio_raw = self._extract_date(
                props.get("Fecha Inicio"), default=datetime.now().isoformat()
            )
            fecha_fin_raw = self._extract_date(
                props.get("Fecha Fin"), default=datetime.now().isoformat()
            )

            return Poliza(
                numero_poliza=numero_poliza,
                aseguradora=aseguradora,
                titular=titular,
                tipo_plan=tipo_plan,
                coberturas=coberturas,
                exclusiones=exclusiones,
                carencia_dias=carencia_dias,
                fecha_inicio=datetime.fromisoformat(fecha_inicio_raw.replace("Z", "+00:00")),
                fecha_fin=datetime.fromisoformat(fecha_fin_raw.replace("Z", "+00:00")),
                estado=estado,
            )
        except Exception as e:
            print(f"❌ Error parseando póliza de Notion: {e}")
            return None


# Singleton
notion_service = NotionService()