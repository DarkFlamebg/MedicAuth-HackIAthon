"""
Servicio del Grafo de Agentes de IA utilizando LangGraph y Gemini 2.5 Flash
"""
import json
import time
import httpx
import tempfile
import pathlib
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
import asyncio

from app.models.authorization import SolicitudAutorizacion, Poliza, DecisionIA, EstadoSolicitud
from app.services.notion_service import notion_service
from app.core.config import settings

# 1. DEFINICIÓN DEL ESTADO MUTUALIZADO (State)
class AuthorizationState(TypedDict):
    """Contenedor de datos que fluye a través de los nodos del grafo"""
    solicitud: SolicitudAutorizacion
    poliza: Poliza
    informe_medico_url: Optional[str] 
    
    # Datos extraídos y evaluados en el flujo
    datos_medicos_extraidos: Optional[Dict[str, Any]]
    auditoria_cobertura_legal: Optional[Dict[str, Any]]
    
    # Control de Calidad / Auto-Crítica
    criticas_encontradas: Optional[List[str]]
    intentos_revision: int
    
    # Resultado estructurado final
    decision_final: Optional[Dict[str, Any]]
    tiempo_inicio: float

# Factory para crear instancias de LLM por nodo
def _get_llm():
    """Crea una nueva instancia de ChatGoogleGenerativeAI para cada nodo"""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.1,
        google_api_key=settings.GEMINI_API_KEY
    )


# 2. IMPLEMENTACIÓN DE NODOS (Agentes Especialistas)

async def nodo_extractor_medico(state: AuthorizationState) -> Dict[str, Any]:
    """Agente que descarga el PDF de Cloudinary y realiza la extracción clínica"""
    print("[AGENTE 1] Extrayendo datos clínicos desde URL de Cloudinary...")
    solicitud = state["solicitud"]
    pdf_url = state.get("informe_medico_url")
    
    # Configuramos el SDK nativo de Google por si necesitamos subir el archivo temporal
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    archivo_gemini = None
    tmp_path = None

    # Si hay una URL válida de Cloudinary, descargamos y creamos el puntero temporal para Gemini
    if pdf_url:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(pdf_url, timeout=30)
                pdf_bytes = response.content

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = tmp.name

            archivo_gemini = genai.upload_file(
                path=tmp_path,
                display_name=f"informe_{solicitud.id_solicitud}.pdf",
                mime_type="application/pdf",
            )
            print("[SUCCESS] PDF descargado de Cloudinary y montado en la API de Gemini")
        except Exception as e:
            print(f"[WARNING] No se pudo procesar el archivo adjunto multimedia: {e}")

    prompt = f"""
    Eres un Médico Auditor experto en el sistema de salud de Ecuador. Analiza la información clínica provista en el documento para rellenar la estructura de control.
    
    Datos de cotejo de la Solicitud:
    - Paciente Esperado: {solicitud.paciente_nombre}
    - Cédula Esperada: {solicitud.cedula}
    - Tipo de Cirugía Solicitada: {solicitud.tipo_cirugia}
    
    Instrucciones Mandatarias:
    1. Verifica si el nombre del paciente y la cédula en el documento coinciden exactamente con los datos de la solicitud.
    2. Identifica el diagnóstico principal y busca su respectivo código CIE-10.
    3. Confirma si el informe cuenta de manera visible con la firma y/o sello del médico tratante.
    4. Extrae los hallazgos clínicos que justifican el procedimiento.
    
    Responde estrictamente en formato JSON válido:
    {{
        "paciente_coincide": true/false,
        "diagnostico_principal": "Texto del diagnóstico",
        "cie10": "Código CIE-10",
        "tiene_firma_sello": true/false,
        "justificacion_clinica_encontrada": true/false,
        "resumen_justificacion": "Breve resumen de la condición médica"
    }}
    """
    
    # Preparamos el payload combinando el archivo de Gemini (si existe) o usando el contexto de texto libre
    payload = []
    if archivo_gemini:
        payload.append(archivo_gemini)
    payload.append(prompt)
    
    # Invocamos la llamada estructurada (usando factory para nueva instancia)
    llm = _get_llm()
    response = await asyncio.to_thread(
        lambda: llm.invoke(payload, response_format={"type": "json_object"})
    )
    
    # Limpieza inmediata del archivo temporal local en el servidor
    if tmp_path:
        pathlib.Path(tmp_path).unlink(missing_ok=True)
        
    try:
        resultado = json.loads(response.content)
    except Exception:
        resultado = {
            "paciente_coincide": False, "diagnostico_principal": "Error de parsing",
            "cie10": "N/A", "tiene_firma_sello": False, "justificacion_clinica_encontrada": False,
            "resumen_justificacion": "Error al procesar el JSON de salida."
        }
        
    return {"datos_medicos_extraidos": resultado}


async def nodo_auditor_legal_tarifario(state: AuthorizationState) -> Dict[str, Any]:
    """Agente Especialista en Pólizas, Exclusiones y Ley de Medicina Prepagada de Ecuador"""
    print("[AGENTE 2] Evaluando coberturas, carencias y marco regulatorio...")
    solicitud = state["solicitud"]
    poliza = state["poliza"]
    datos_medicos = state["datos_medicos_extraidos"] or {}
    
    # Calcular días transcurridos desde el inicio de la póliza hasta la cirugía
    dias_desde_inicio = (solicitud.fecha_solicitada.replace(tzinfo=None) - poliza.fecha_inicio.replace(tzinfo=None)).days
    carencia_superada = dias_desde_inicio >= poliza.carencia_dias
    
    prompt = f"""
    Eres un Abogado y Liquidador de Seguros Médicos en Ecuador. Debes auditar la solicitud quirúrgica confrontándola con las condiciones de la póliza y el marco legal aplicable (Ley de Compañías de Medicina Prepagada de Ecuador).
    
    Información para análisis:
    - Tipo de Cirugía: {solicitud.tipo_cirugia}
    - Diagnóstico Clínico (CIE-10): {datos_medicos.get('diagnostico_principal')} ({datos_medicos.get('cie10')})
    - Estado de la Póliza: {poliza.estado}
    - Plan contratado: {poliza.tipo_plan}
    - Exclusiones explícitas de la póliza: {", ".join(poliza.exclusiones)}
    - Coberturas contratadas (JSON): {json.dumps(poliza.coberturas, ensure_ascii=False)}
    - Carencia requerida contractual: {poliza.carencia_dias} días
    - ¿Superó el periodo de carencia normal en base a fechas?: {carencia_superada}
    
    Consideraciones Legales Mandatarias (Ecuador):
    1. Según el Art. 31 de la Ley de Medicina Prepagada, si el caso constituye una EMERGENCIA MÉDICA VITAL que compromete la vida del paciente, no se pueden aplicar periodos de carencia ni exclusiones de preexistencias de forma inmediata.
    2. Valida si el tipo de cirugía o el diagnóstico clínico se encuentran textualmente o por asociación directa en la lista de exclusiones de la póliza.
    
    Responde estrictamente en formato JSON válido con la siguiente estructura:
    {{
        "procedimiento_cubierto": true/false,
        "clausulas_aplicadas": ["Lista de exclusiones o coberturas evaluadas"],
        "aplica_emergencia_vital_art31": true/false,
        "motivo_legal_auditoria": "Explicación clara sustentada en las pólizas y la ley",
        "documentos_faltantes_detectados": ["Cédula", "Exámenes de Laboratorio", etc. Si aplica, sino dejar vacío]
    }}
    """
    
    llm = _get_llm()
    response = await asyncio.to_thread(
        lambda: llm.invoke(prompt, response_format={"type": "json_object"})
    )
    try:
        resultado = json.loads(response.content)
    except Exception:
        resultado = {
            "procedimiento_cubierto": False, "clausulas_aplicadas": [],
            "aplica_emergencia_vital_art31": False, "motivo_legal_auditoria": "Error de parsing en nodo legal",
            "documentos_faltantes_detectados": []
        }
        
    return {"auditoria_cobertura_legal": resultado}


async def nodo_supervisor_critico(state: AuthorizationState) -> Dict[str, Any]:
    """Nodo Supervisor (Self-Reflection): Control de calidad de la decisión final antes de emitir veredicto"""
    print("[SUPERVISOR CRÍTICO] Verificando consistencia y detectando alucinaciones...")
    solicitud = state["solicitud"]
    datos_medicos = state["datos_medicos_extraidos"] or {}
    auditoria_legal = state["auditoria_cobertura_legal"] or {}
    
    criticas = []
    
    # Reglas lógicas duras (Guardrails) de control de calidad
    if not datos_medicos.get("paciente_coincide"):
        criticas.append("El nombre o la cédula del informe médico digitalizado no concuerdan con la solicitud cargada.")
        
    if not datos_medicos.get("tiene_firma_sello"):
        criticas.append("El informe médico carece de la firma o el sello oficial requerido del profesional tratante.")
        
    if auditoria_legal.get("procedimiento_cubierto") is False and auditoria_legal.get("aplica_emergencia_vital_art31") is True:
        # Contradicción médica benigna: No cubre por contrato, pero la Ley de Ecuador obliga por emergencia vital
        pass
    elif auditoria_legal.get("procedimiento_cubierto") is False and not auditoria_legal.get("motivo_legal_auditoria"):
        criticas.append("Se está denegando la cobertura sin especificar la justificación jurídica o la cláusula de exclusión contractual.")

    return {
        "criticas_encontradas": criticas, 
        "intentos_revision": state.get("intentos_revision", 0) + 1
    }


async def nodo_compilador_informe(state: AuthorizationState) -> Dict[str, Any]:
    """Compila el JSON final estructurado que encaja exactamente con el esquema Pydantic DecisionIA"""
    print("[COMPILADOR FINAL] Generando dictamen oficial estructurado...")
    solicitud = state["solicitud"]
    datos_medicos = state["datos_medicos_extraidos"] or {}
    auditoria_legal = state["auditoria_cobertura_legal"] or {}
    criticas = state.get("criticas_encontradas", [])
    
    # La aprobación final depende de la viabilidad legal o del amparo de emergencia del Art. 31
    es_viable = auditoria_legal.get("procedimiento_cubierto", False) or auditoria_legal.get("aplica_emergencia_vital_art31", False)
    
    # Si arrastra críticas de identidad o falta de firmas de seguridad, se rechaza/suspende de inmediato
    if criticas:
        es_viable = False
        
    # Calcular score de confianza algorítmicamente basado en la solidez de los datos recopilados
    score = 95.0
    if criticas: score -= 30.0
    if not datos_medicos.get("tiene_firma_sello"): score -= 15.0
    if datos_medicos.get("cie10") == "N/A": score -= 10.0
    score = max(10.0, min(100.0, score))
    
    # Construcción del razonamiento en formato Markdown elegante para la UI médica
    razonamiento_md = f"""### 🩺 Dictamen Técnico de Auditoría Inteligente

**Estado del Dictamen:** {"🟢 APROBADO CON COBERTURA" if es_viable else "🔴 DENEGADO / REQUIERE REVISIÓN"}

#### 1. Hallazgos Clínicos (Extracción Automática):
* **Diagnóstico Detectado:** {datos_medicos.get('diagnostico_principal')}
* **Código CIE-10:** `{datos_medicos.get('cie10')}`
* **Sustento Clínico:** {datos_medicos.get('resumen_justificacion')}
* **Validación de Identidad:** {"Sincronizado correctamente" if datos_medicos.get('paciente_coincide') else "⚠️ ALERTA: No coincide la documentación"}

#### 2. Fundamentos Jurídicos y Contractuales (Legislación de Ecuador):
* **Sustento Operativo:** {auditoria_legal.get('motivo_legal_auditoria')}
* **Aplicación Art. 31 (Emergencia Vital):** {"Sí, amparado bajo la ley de Medicina Prepagada" if auditoria_legal.get('aplica_emergencia_vital_art31') else "No aplica para este escenario clínico"}
* **Cláusulas Evaluadas:** {", ".join(auditoria_legal.get('clausulas_aplicadas', [])) or "Ninguna restrictiva"}
"""

    if criticas:
        razonamiento_md += "\n#### ⚠️ Errores Críticos Detectados en Auditoría:\n" + "\n".join([f"* {c}" for c in criticas])

    decision_ia_dict = {
        "aprobado": es_viable,
        "razonamiento": razonamiento_md.strip(),
        "score_confianza": score,
        "clausulas_relevantes": auditoria_legal.get("clausulas_aplicadas", []),
        "documentos_faltantes": auditoria_legal.get("documentos_faltantes_detectados", []) or ([] if not criticas else ["Informe Médico Con Firma/Sello Válido"]),
        "recomendaciones": "Remitir a auditoría de segundo nivel para validación manual de preexistencias." if not es_viable else "Proceder con la programación de quirófano y liquidación de haberes médicos."
    }
    
    return {"decision_final": decision_ia_dict}


async def nodo_notion_saver(state: AuthorizationState) -> Dict[str, Any]:
    """Nodo Finalizador: Sincroniza en segundo plano toda la información procesada directamente en Notion"""
    print("[NOTION SAVER] Persistiendo datos y veredicto final en la base de datos de Notion...")
    solicitud = state["solicitud"]
    decision = state["decision_final"]
    
    # Mapear bandera booleana a las categorías select que configuraste en tu Notion
    nuevo_estado = EstadoSolicitud.APROBADO.value if decision["aprobado"] else EstadoSolicitud.RECHAZADO.value
    if decision["documentos_faltantes"]:
        nuevo_estado = EstadoSolicitud.DOCUMENTOS_FALTANTES.value
        
    tiempo_total = time.time() - state["tiempo_inicio"]
    
    # Ejecutamos la llamada asíncrona oficial reutilizando tu NotionService intacto
    await notion_service.update_authorization_status(
        page_id=solicitud.id_solicitud,
        status=nuevo_estado,
        decision=decision,
        reasoning=decision["razonamiento"],
        confidence=decision["score_confianza"],
        missing_docs=decision["documentos_faltantes"],
        processing_time=tiempo_total
    )
    
    return {}


# 4. DIRECCIONAMIENTO CONDICIONAL (Routing)
async def enrutador_control_calidad(state: AuthorizationState):
    """Evalúa si el flujo debe ciclar para corrección o avanzar al guardado final"""
    criticas = state.get("criticas_encontradas", [])
    intentos = state.get("intentos_revision", 0)
    
    # Si hay errores lógicos pero tenemos margen de intentos, devolvemos al auditor para auto-corregir
    if criticas and intentos < 2:
        print(f"⚠️ El supervisor detectó inconsistencias. Re-enrutando para auto-corrección (Intento {intentos})...")
        return "auditor_legal"
    
    # Si todo está limpio o ya superamos el límite del ciclo, consolidamos el reporte
    return "compilador"


# 5. ENSAMBLAJE TOTAL DEL FLUJO DE TRABAJO (Workflow Graph)
workflow = StateGraph(AuthorizationState)

# Registrar todos nuestros nodos independientes
workflow.add_node("extractor_medico", nodo_extractor_medico)
workflow.add_node("auditor_legal", nodo_auditor_legal_tarifario)
workflow.add_node("supervisor_control", nodo_supervisor_critico)
workflow.add_node("compilador", nodo_compilador_informe)
workflow.add_node("notion_saver", nodo_notion_saver)

# Configurar el camino de ejecución
workflow.set_entry_point("extractor_medico")
workflow.add_edge("extractor_medico", "auditor_legal")
workflow.add_edge("auditor_legal", "supervisor_control")

# Agregar bifurcación condicional basada en la crítica de calidad
workflow.add_conditional_edges(
    "supervisor_control",
    enrutador_control_calidad,
    {
        "auditor_legal": "auditor_legal",
        "compilador": "compilador"
    }
)

workflow.add_edge("compilador", "notion_saver")
workflow.add_edge("notion_saver", END)

# Compilar el grafo final ejecutable
grafo_agente_autorizador = workflow.compile()