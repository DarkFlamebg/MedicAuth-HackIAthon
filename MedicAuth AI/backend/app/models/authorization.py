"""
Modelos de datos para la aplicación
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class EstadoSolicitud(str, Enum):
    """Estados posibles de una solicitud"""
    PENDIENTE = "Pendiente"
    APROBADO = "Aprobado"
    RECHAZADO = "Rechazado"
    DOCUMENTOS_FALTANTES = "Documentos Faltantes"

class TipoCirugia(str, Enum):
    """Tipos de cirugía comunes"""
    APENDICECTOMIA = "Apendicectomía"
    CESAREA = "Cesárea"
    HISTERECTOMIA = "Histerectomía"
    COLECISTECTOMIA = "Colecistectomía"
    HERNIA = "Reparación de Hernia"
    ARTROSCOPIA = "Artroscopía"
    OTRO = "Otro"

class Patient(BaseModel):
    """Información del paciente"""
    nombre: str
    cedula: str
    edad: int
    
class SolicitudAutorizacion(BaseModel):
    """Modelo de solicitud de autorización quirúrgica"""
    id_solicitud: str
    paciente_nombre: str
    cedula: str
    edad: int
    numero_poliza: str
    tipo_cirugia: str
    fecha_solicitada: datetime
    hospital: str
    medico_tratante: str
    informe_medico_url: Optional[str] = None
    estado: EstadoSolicitud = EstadoSolicitud.PENDIENTE
    decision_ia: Optional[Dict[str, Any]] = None
    razonamiento: Optional[str] = None
    score_confianza: Optional[float] = None
    documentos_faltantes: List[str] = []
    fecha_respuesta: Optional[datetime] = None
    tiempo_procesamiento: Optional[float] = None
    
    class Config:
        use_enum_values = True

class EstadoPoliza(str, Enum):
    """Estados de póliza"""
    ACTIVA = "Activa"
    SUSPENDIDA = "Suspendida"
    VENCIDA = "Vencida"

class TipoPlan(str, Enum):
    """Tipos de plan de seguro"""
    BASICO = "Básico"
    PREMIUM = "Premium"
    VIP = "VIP"
    AMBULATORIO = "Ambulatorio"
    HOSPITALARIO = "Hospitalario"
    MATERNIDAD = "Maternidad"
    DENTAL = "Dental"
    INTERNACIONAL = "Internacional"
    CORPORATIVO = "Corporativo"
    FAMILIAR = "Familiar"


class Poliza(BaseModel):
    """Modelo de póliza de seguro"""
    numero_poliza: str
    aseguradora: str
    titular: str
    tipo_plan: TipoPlan
    coberturas: Dict[str, Any]  # JSON con detalles de coberturas
    exclusiones: List[str]
    carencia_dias: int
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: EstadoPoliza
    documento_poliza_url: Optional[str] = None
    
    class Config:
        use_enum_values = True

class DecisionIA(BaseModel):
    """Respuesta del agente de IA"""
    aprobado: bool
    razonamiento: str
    score_confianza: float = Field(..., ge=0, le=100)
    clausulas_relevantes: List[str] = []
    documentos_faltantes: List[str] = []
    recomendaciones: Optional[str] = None
    tiempo_procesamiento: float
    
class WebhookNotionPayload(BaseModel):
    """Payload del webhook de Notion"""
    page_id: str
    database_id: str
    properties: Dict[str, Any]
    created_time: Optional[str] = None
    last_edited_time: Optional[str] = None
