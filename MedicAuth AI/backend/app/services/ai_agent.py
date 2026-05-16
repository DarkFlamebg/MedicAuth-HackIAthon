"""
Agente de IA para análisis y autorización quirúrgica
"""

from anthropic import Anthropic
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import time

from app.core.config import settings
from app.models.authorization import SolicitudAutorizacion, Poliza, DecisionIA

class AIAgent:
    """Agente de IA multi-step para autorización quirúrgica"""
    
    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"
    
    async def process_authorization(
        self,
        solicitud: SolicitudAutorizacion,
        poliza: Poliza,
        informe_medico_text: Optional[str] = None
    ) -> DecisionIA:
        """
        Procesa una solicitud de autorización quirúrgica
        
        Pasos:
        1. Analizar informe médico
        2. Validar cobertura en póliza (RAG)
        3. Verificar período de carencia
        4. Emitir decisión con razonamiento
        """
        start_time = time.time()
        
        try:
            # Construir prompt para Claude
            prompt = self._build_authorization_prompt(
                solicitud=solicitud,
                poliza=poliza,
                informe_medico=informe_medico_text
            )
            
            # Llamar a Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,  # Más determinista para decisiones médicas
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extraer respuesta
            response_text = response.content[0].text
            
            # Parsear respuesta JSON
            decision_data = self._parse_ai_response(response_text)
            
            processing_time = time.time() - start_time
            
            return DecisionIA(
                aprobado=decision_data.get("aprobado", False),
                razonamiento=decision_data.get("razonamiento", ""),
                score_confianza=decision_data.get("score_confianza", 0),
                clausulas_relevantes=decision_data.get("clausulas_relevantes", []),
                documentos_faltantes=decision_data.get("documentos_faltantes", []),
                recomendaciones=decision_data.get("recomendaciones"),
                tiempo_procesamiento=processing_time
            )
            
        except Exception as e:
            print(f"❌ Error en agente IA: {e}")
            # Decisión por defecto en caso de error
            return DecisionIA(
                aprobado=False,
                razonamiento=f"Error en el procesamiento: {str(e)}",
                score_confianza=0,
                clausulas_relevantes=[],
                documentos_faltantes=["Error en análisis - requiere revisión manual"],
                recomendaciones="Contactar con equipo técnico",
                tiempo_procesamiento=time.time() - start_time
            )
    
    def _build_authorization_prompt(
        self,
        solicitud: SolicitudAutorizacion,
        poliza: Poliza,
        informe_medico: Optional[str]
    ) -> str:
        """Construye el prompt para Claude"""
        
        # Calcular días desde inicio de póliza
        dias_desde_inicio = (datetime.now() - poliza.fecha_inicio).days
        cumple_carencia = dias_desde_inicio >= poliza.carencia_dias
        
        prompt = f"""Eres un experto en análisis de autorizaciones médicas para cirugías. 

INFORMACIÓN DEL PACIENTE:
- Nombre: {solicitud.paciente_nombre}
- Edad: {solicitud.edad} años
- Cédula: {solicitud.cedula}
- Hospital: {solicitud.hospital}
- Médico tratante: {solicitud.medico_tratante}

CIRUGÍA SOLICITADA:
- Tipo: {solicitud.tipo_cirugia}
- Fecha solicitada: {solicitud.fecha_solicitada.strftime('%Y-%m-%d')}

INFORMACIÓN DE LA PÓLIZA:
- Número: {poliza.numero_poliza}
- Aseguradora: {poliza.aseguradora}
- Tipo de plan: {poliza.tipo_plan}
- Estado: {poliza.estado}
- Días desde inicio de póliza: {dias_desde_inicio} días
- Período de carencia: {poliza.carencia_dias} días
- ¿Cumple carencia?: {"SÍ ✓" if cumple_carencia else "NO ✗"}

COBERTURAS DE LA PÓLIZA:
{json.dumps(poliza.coberturas, indent=2, ensure_ascii=False)}

EXCLUSIONES:
{chr(10).join(f"- {exc}" for exc in poliza.exclusiones)}

{"INFORME MÉDICO:" if informe_medico else "INFORME MÉDICO: No disponible"}
{informe_medico if informe_medico else "Sin informe médico adjunto"}

INSTRUCCIONES:
Analiza cuidadosamente toda la información y determina si la cirugía debe ser APROBADA o RECHAZADA.

Considera:
1. ¿El procedimiento está cubierto en el plan?
2. ¿Se cumple el período de carencia?
3. ¿Hay exclusiones que apliquen?
4. ¿El informe médico justifica la necesidad del procedimiento?
5. ¿Falta algún documento crítico?

RESPONDE ÚNICAMENTE CON UN JSON EN ESTE FORMATO:
{{
  "aprobado": true o false,
  "razonamiento": "Explicación detallada de la decisión paso a paso",
  "score_confianza": número entre 0 y 100,
  "clausulas_relevantes": ["Cláusula 1", "Cláusula 2"],
  "documentos_faltantes": ["Documento 1", "Documento 2"] o [],
  "recomendaciones": "Recomendaciones adicionales si aplica"
}}

No incluyas ningún texto fuera del JSON.
"""
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parsea la respuesta de Claude a un diccionario"""
        try:
            # Eliminar markdown si existe
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            
            clean_text = clean_text.strip()
            
            # Parsear JSON
            data = json.loads(clean_text)
            return data
            
        except json.JSONDecodeError as e:
            print(f"❌ Error parseando respuesta JSON: {e}")
            print(f"Respuesta original: {response_text[:500]}...")
            
            # Fallback: extraer información manualmente
            return {
                "aprobado": False,
                "razonamiento": response_text[:500],
                "score_confianza": 50,
                "clausulas_relevantes": [],
                "documentos_faltantes": ["Error en análisis automático"],
                "recomendaciones": "Requiere revisión manual"
            }

# Singleton
ai_agent = AIAgent()
