import time
from app.models.authorization import SolicitudAutorizacion, Poliza, DecisionIA
from app.services.agent_workflow import grafo_agente_autorizador

class AIAgent:
    def __init__(self):
        pass

    async def process_authorization(
        self,
        solicitud: SolicitudAutorizacion,
        poliza: Poliza
    ) -> DecisionIA:
        """
        Punto de entrada asíncrono que ejecuta la arquitectura multi-agente reflectiva
        leyendo el informe directamente desde la URL de Cloudinary almacenada.
        """
        print(f"\n🚀 [INICIANDO AUDITORÍA EN GRAFO] Solicitud ID: {solicitud.id_solicitud}")
        start_time = time.time()
        
        # Inyectamos directamente la URL de Cloudinary que ya viene mapeada en la solicitud
        initial_state = {
            "solicitud": solicitud,
            "poliza": poliza,
            "informe_medico_url": solicitud.informe_medico_url,  # <--- URL Segura de Cloudinary
            "datos_medicos_extraidos": None,
            "auditoria_cobertura_legal": None,
            "criticas_encontradas": [],
            "intentos_revision": 0,
            "decision_final": None,
            "tiempo_inicio": start_time
        }
        
        try:
            # Invocar el grafo asíncronamente
            final_output = await grafo_agente_autorizador.ainvoke(initial_state)
            decision_dict = final_output["decision_final"]
            tiempo_total = time.time() - start_time
            
            return DecisionIA(
                aprobado=decision_dict["aprobado"],
                razonamiento=decision_dict["razonamiento"],
                score_confianza=decision_dict["score_confianza"],
                clausulas_relevantes=decision_dict["clausulas_relevantes"],
                documentos_faltantes=decision_dict["documentos_faltantes"],
                recomendaciones=decision_dict["recomendaciones"],
                tiempo_procesamiento=tiempo_total
            )
            
        except Exception as e:
            print(f" [CRITICAL ERROR EN GRAFO] Falló la ejecución: {e}")
            return DecisionIA(
                aprobado=False,
                razonamiento=f"Error crítico en el motor de ejecución del grafo de agentes: {str(e)}",
                score_confianza=0.0,
                clausulas_relevantes=[],
                documentos_faltantes=["Re-procesamiento Técnico Requerido"],
                recomendaciones="Contactar de inmediato con soporte técnico.",
                tiempo_procesamiento=time.time() - start_time
            )

# Singleton
ai_agent = AIAgent()