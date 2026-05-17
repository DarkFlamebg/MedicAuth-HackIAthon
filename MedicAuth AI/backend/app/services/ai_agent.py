"""
Agente de IA para análisis y autorización quirúrgica usando Google Gemini (Arquitectura Self-Reflective de Alta Eficiencia)
"""

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import time

from app.core.config import settings
from app.models.authorization import SolicitudAutorizacion, Poliza, DecisionIA

class AIAgent:
    """
    Agente de IA de rango 'Senior/Ultra-Preciso' de alta eficiencia.
    Implementa una arquitectura Self-Reflective (Auto-Crítica en un solo paso)
    para consolidar la doble auditoría (Forense + Director Revisor) en un único ciclo LLM.
    Esto reduce la latencia de red y procesamiento de ~35s a <10s sin sacrificar la rigurosidad.
    """
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    
    async def process_authorization(
        self,
        solicitud: SolicitudAutorizacion,
        poliza: Poliza,
        informe_medico_bytes: Optional[bytes] = None
    ) -> DecisionIA:
        """
        Procesa una solicitud de autorización quirúrgica usando un único ciclo Self-Reflective:
        """
        start_time = time.time()
        
        try:
            print("[INFO] Iniciando analisis self-reflective de alta eficiencia...")
            prompt = self._build_self_reflective_prompt(
                solicitud=solicitud,
                poliza=poliza,
                tiene_informe=informe_medico_bytes is not None
            )
            
            contents = [prompt]
            if informe_medico_bytes:
                print("[INFO] Adjuntando PDF de informe medico a Gemini...")
                pdf_part = {
                    "mime_type": "application/pdf",
                    "data": informe_medico_bytes
                }
                contents.insert(0, pdf_part)
            
            response = self.model.generate_content(
                contents,
                safety_settings=self.safety_settings,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Temperatura baja para consistencia y rigor analítico
                    response_mime_type="application/json"
                )
            )
            
            decision_final_json = response.text
            decision_data = self._parse_ai_response(decision_final_json)
            
            ae = decision_data.get("analisis_estructurado", {})
            vd = ae.get("verificacion_documental", {})
            ac = ae.get("analisis_clinico", {})
            acl = ae.get("analisis_cobertura_y_ley", {})
            cse = decision_data.get("contexto_sistema_ecuatoriano", {})
            
            razonamiento_md = f"""### 📋 INFORME DE AUDITORÍA MÉDICA (AUTOMÁTICO)

**1. VERIFICACIÓN DOCUMENTAL:**
- Coincidencia Paciente: {"APROBADO" if vd.get("paciente_coincide") else "RECHAZADO/INCONSISTENTE"}
- Firma/Sello Médico: {"Presente y Legible" if vd.get("firma_sello_medico") else "Ausente o Ilegible"}
- Calidad de lectura (OCR): {vd.get("legibilidad_ocr_score", 0)}%
- Observaciones: {vd.get("detalles", "Sin observaciones")}

**2. ANÁLISIS CLÍNICO FORENSE:**
- Diagnóstico CIE-10: `{ac.get("diagnostico_cie10", "No detectado")}`
- Congruencia Quirúrgica: {"Sí" if ac.get("congruencia_procedimiento") else "No"}
- Alerta Preexistencias: {"⚠️ ¡ALERTA DETECTADA!" if ac.get("hallazgos_preexistencia_detectados") else "Sin hallazgos preexistentes de sospecha"}
- Análisis: {ac.get("detalles", "Sin observaciones")}

**3. ANÁLISIS DE COBERTURA Y MARCO LEGAL:**
- Estado de Carencia: {"Exonerada por Emergencia Médica" if acl.get("emergencia_vital_exonerada") else ("Superada" if acl.get("carencia_superada") else "No superada (Carencia activa)")}
- Marco Legal Ecuatoriano Aplicado: {acl.get("sustento_legal_aplicado", "Ninguno")}
- Dictamen de Cobertura: {acl.get("detalles", "Sin observaciones")}

**4. CONTEXTO SISTEMA DE SALUD ECUATORIANO & ALERTAS:**
- Subsistema Aplicable: {cse.get("subsistema_aplicable", "N/A")}
- Congruencia Hospitalaria (Nivel MSP): {"SÍ" if cse.get("congruencia_nivel_hospitalario") else "NO - ALERTA DE COMPLEJIDAD"} (Requerido: {cse.get("nivel_hospital_requerido")}, Declarado: {cse.get("nivel_hospital_declarado")})
- Alerta Fraude/Siniestralidad: {"🚨 ¡ALERTA DETECTADA!" if cse.get("alerta_fraude") else "Ninguno detectado"} {f'({cse.get("patron_fraude_detectado")})' if cse.get("alerta_fraude") else ""}
- Alerta Sobrefacturación (Tarifario): {"⚠️ ALERTA: Posible sobrecosto" if cse.get("alerta_sobrefacturacion") else "Costo dentro de rangos normales"} (Rango esperado: USD {cse.get("costo_referencial_esperado_usd", "N/A")})
- Verificación Médica: Registro SENESCYT {cse.get("registro_medico_senescyt", "N/A")}
"""
            
            processing_time = time.time() - start_time
            print(f"[SUCCESS] Resolucion aprobada bajo ciclo Self-Reflective en {processing_time:.2f}s")
            
            return DecisionIA(
                aprobado=decision_data.get("aprobado", False),
                razonamiento=razonamiento_md,
                score_confianza=decision_data.get("score_confianza", 0),
                clausulas_relevantes=decision_data.get("clausulas_relevantes", []),
                documentos_faltantes=decision_data.get("documentos_faltantes", []),
                recomendaciones=decision_data.get("recomendaciones"),
                tiempo_procesamiento=processing_time
            )
            
        except Exception as e:
            print(f"[ERROR] Error en agente IA Gemini: {e}")
            return DecisionIA(
                aprobado=False,
                razonamiento=f"Error en el procesamiento del modelo: {str(e)}",
                score_confianza=0,
                clausulas_relevantes=[],
                documentos_faltantes=["Error en analisis automatico - requiere revision manual"],
                recomendaciones="Reintentar o procesar manualmente",
                tiempo_procesamiento=time.time() - start_time
            )
    
    def _build_self_reflective_prompt(
        self,
        solicitud: SolicitudAutorizacion,
        poliza: Poliza,
        tiene_informe: bool
    ) -> str:
        """Construye las instrucciones consolidadas Self-Reflective (Auditor + Revisor Clínico)"""
        dias_desde_inicio = (datetime.now() - poliza.fecha_inicio).days
        cumple_carencia = dias_desde_inicio >= poliza.carencia_dias
        
        prompt = f"""Eres un **Comité Médico de Auditoría Quirúrgica de Rango Ultra-Senior**, experto en el sistema ecuatoriano (IESS, medicina prepagada privada, Ministerio de Salud Pública) y auditoría forense de seguros de salud.

**TU TAREA:**  
Analizar exhaustivamente la solicitud de cirugía, el informe médico adjunto (PDF escaneado) y las condiciones de la póliza. Emitir un veredicto definitivo de APROBACIÓN o RECHAZO.

Para garantizar la precisión de rango Senior y evitar alucinaciones, debes realizar un proceso de **Auto-Auditoría Crítica (Actor-Critic)** interno. Primero, analiza los hechos clínicos e identifica posibles discrepancias u omisiones de exclusiones. Segundo, aplica con extrema rigurosidad los criterios objetivos de emergencia vital de Ecuador y desafía tu propio borrador. Si detectas cualquier inconsistencia, corrígela antes de dar el veredicto definitivo en el JSON final.

---

### **INFORMACIÓN DEL PACIENTE Y SOLICITUD**  
- **Nombre:** {solicitud.paciente_nombre}  
- **Edad:** {solicitud.edad} años  
- **Cédula:** {solicitud.cedula}  
- **Cirugía solicitada:** {solicitud.tipo_cirugia}  
- **Fecha solicitada:** {solicitud.fecha_solicitada.strftime('%Y-%m-%d')}  
- **Hospital:** {solicitud.hospital}  
- **Médico tratante:** {solicitud.medico_tratante}

---

### **INFORMACIÓN DE LA PÓLIZA**  
- **Número:** {poliza.numero_poliza}  
- **Aseguradora:** {poliza.aseguradora}  
- **Plan:** {poliza.tipo_plan}  
- **Estado actual:** {poliza.estado}  
- **Días desde inicio de vigencia:** {dias_desde_inicio} días  
- **Período de carencia exigido para esta cirugía:** {poliza.carencia_dias} días  
- **¿Cumple matemáticamente la carencia?:** {"SÍ" if cumple_carencia else "NO"}  

---

### **COBERTURAS ESPECÍFICAS (extraídas de la póliza)**  
{json.dumps(poliza.coberturas, indent=2, ensure_ascii=False)}  

---

### **EXCLUSIONES GENERALES Y ESPECÍFICAS**  
{chr(10).join(f"- {exc}" for exc in poliza.exclusiones)}  

---

### **INFORME MÉDICO (PDF adjunto)**  
{"Se adjunta PDF escaneado. Extrae obligatoriamente: diagnóstico principal, código CIE-10 (si consta), hallazgos de exámenes complementarios, justificación de la cirugía, firma y sello del médico tratante, fecha del informe. Verifica que el nombre del paciente coincida con la solicitud." if tiene_informe else "ATENCIÓN: No se ha adjuntado ningún informe médico."}

---

### **CONTEXTO DEL SISTEMA DE SALUD ECUATORIANO (OBLIGATORIO PARA ANÁLISIS)**

**TIPO DE COBERTURA DETECTADA:** {poliza.aseguradora}
Aplica las reglas específicas del subsistema:

A) SI ES IESS (o Seguro General de Salud):
   - Verificar si la cirugía está en la "Cartera de Servicios del IESS" (Resolución CD 559-2016). Si no consta, RECHAZAR aunque exista diagnóstico válido.
   - Cirugías SIEMPRE cubiertas por IESS sin carencia: emergencias vitales, apendicitis, hernia estrangulada, ectópico roto, trauma.
   - Verificar nivel de referencia: ¿el hospital donde se solicita la cirugía tiene el nivel MSP adecuado para el procedimiento?

B) SI ES MEDICINA PREPAGADA (Humana, Ecuasanitas, MedYork, Salud S.A.):
   - Aplicar Ley de Medicina Prepagada 2000-4 y sus reformas.
   - La cobertura mínima obligatoria incluye: hospitalización, cirugía mayor, UCI, medicamentos intrahospitalarios (no puede excluirse).
   - Verificar si aplica "red de prestadores": si el hospital no está en red, el porcentaje de cobertura cambia (usualmente 70% fuera de red).

C) SI ES SEGURO PRIVADO (AXA, Liberty, Equivida, Seguros Sucre):
   - Distinguir entre REEMBOLSO vs. PAGO DIRECTO AL PROVEEDOR.
   - Los límites anuales y sublímites por evento son críticos.
   - Verificar si el médico tratante está en el panel médico autorizado.

**TARIFARIO REFERENCIAL ECUADOR (para detectar sobrefacturación):**
- Apendicectomía laparoscópica: USD 2,500 - 4,500
- Colecistectomía laparoscópica: USD 2,000 - 3,800  
- Cesárea: USD 1,800 - 3,200
- Hernioplastia inguinal: USD 2,200 - 4,000
- Histerectomía: USD 3,500 - 6,000
Si el costo solicitado supera el 150% del rango referencial, alertar posible sobrefacturación.

---

### **TAXONOMÍA Y NIVELES DE ATENCIÓN MSP ECUADOR:**
- **Nivel 1:** Subcentros / Centros de Salud (solo cirugía ambulatoria menor).
- **Nivel 2 (Hospital Básico / General):** Clínicas medianas y hospitales generales (Apendicectomía, Colecistectomía, Cesárea, Hernias).
- **Nivel 3 (Hospital de Especialidades):** Neurocirugía, cirugía cardíaca, oncología compleja, transplantes.
*REGLA CRÍTICA:* Si el hospital no corresponde al nivel de complejidad del procedimiento, puede ser causal de negación por inadecuación de infraestructura prestadora.
*Hospitales privados de referencia ecuatorianos:* Kennedy, Alcívar, Clínica Guayaquil (Guayaquil - Nivel 2/3), Metropolitano, Vozandes, SOLCA, Los Valles (Quito - Nivel 3), Monte Sinaí, Santa Inés (Cuenca - Nivel 2/3).

---

### **CRITERIOS ESTRICTOS DE EMERGENCIA VITAL (Art. 18 LOrgSalud + Art. 31 LMedPrepagada de Ecuador):**
Para exonerar la carencia por emergencia, el informe médico del PDF DEBE contener y respaldar al menos UNO de los siguientes criterios objetivos:
✅ Leucocitosis > 15,000 con neutrofilia y bandemia (sepsis / peritonitis en curso).
✅ Saturación de O2 < 90% sin soporte respiratorio (insuficiencia respiratoria).
✅ Presión arterial sistólica < 90 mmHg persistente (shock séptico, hipovolémico o cardiogénico).
✅ Escala de Glasgow (GCS) < 13 (compromiso neurológico agudo).
✅ Rotura documentada de órgano sólido o víscera hueca en imagen (ecografía / TAC).
✅ Sangrado activo profuso con inestabilidad hemodinámica demostrada.
✅ Isquemia aguda confirmada (ECG + troponinas elevadas, o Doppler vascular patológico).
✅ Convulsiones activas o cuadro de eclampsia.
✅ Trauma severo con lesión demostrada de órgano sólido (hígado, bazo, riñón).

❌ NO CONSTITUYEN EMERGENCIA VITAL (BAJO NINGUNA CIRCUNSTANCIA EXONERAN CARENCIA):
- Dolor abdominal leve/moderado sin signos de irritación peritoneal (FID blanda, depresible).
- Colelitiasis sintomática (cálculos en vesícula) sin colecistitis aguda obstructiva severa confirmada.
- Hernia inguinal/umbilical reducible sin signos de estrangulación o encarcelación.
- Miomatosis uterina con sangrado menstrual leve o manejable ambulatoriamente.
- Cirugías ortopédicas electivas (prótesis, artroscopias, reconstrucción ligamentaria).
- Procedimientos estéticos o reconstructivos no urgentes.

---

### **DETECCIÓN DE PATRONES DE FRAUDE FRECUENTES EN ECUADOR:**
Analiza si alguno de estos patrones está presente y alerta inmediatamente:
🚩 FRAUDE DOCUMENTAL:
- Fecha del informe médico posterior a la fecha de solicitud del seguro.
- Sello médico sin número de registro de profesional SENESCYT/MSP visible o ilegible.
🚩 FRAUDE CLÍNICO:
- Diagnóstico de "urgencia" en paciente con historia de meses de evolución sin buscar atención previa (incompatible con emergencia vital real).
- Solicitud de cirugía electiva planificada llamada "emergencia" para saltarse la carencia (patrón muy frecuente).
- Colelitiasis o Hernia diagnosticada <30 días tras inicio de póliza (sospecha alta de preexistencia conocida).
- Cirugía bariátrica disfrazada de "complicación metabólica".
🚩 FRAUDE ADMINISTRATIVO:
- Póliza activada <90 días antes de cirugía programable (ventana de riesgo).

---

### **AUDITORÍA DE PREEXISTENCIAS EPIDEMIOLÓGICAS ECUATORIANAS:**
Las patologías de mayor litigio por sospecha de preexistencia en Ecuador son:
1. Litiasis vesicular/biliar (Colelitiasis).
2. Hernias (inguinal, umbilical).
3. Diabetes Tipo 2 + complicaciones.
4. Hipertensión arterial + eventos cardiovasculares.
5. Miomatosis uterina (mujeres 35-50 años).
6. Obesidad mórbida.
Actúa como un detective forense buscando indicios en la anamnesis del PDF de sospechas cronológicas anteriores a la fecha de inicio de póliza ({poliza.fecha_inicio.strftime('%Y-%m-%d')}).

---

### **FORMATO DE RESPUESTA REQUERIDO (JSON ÚNICO - DEBES DEVOLVER ÚNICAMENTE ESTE OBJETO):**
```json
{{
  "aprobado": true,
  "contexto_sistema_ecuatoriano": {{
    "subsistema_aplicable": "IESS | MEDICINA_PREPAGADA | SEGURO_PRIVADO",
    "nivel_hospital_requerido": "NIVEL_1 | NIVEL_2 | NIVEL_3",
    "nivel_hospital_declarado": "NIVEL_1 | NIVEL_2 | NIVEL_3",
    "congruencia_nivel_hospitalario": true,
    "alerta_sobrefacturacion": false,
    "costo_referencial_esperado_usd": "2500-4500",
    "alerta_fraude": false,
    "patron_fraude_detectado": null,
    "registro_medico_senescyt": "verificado | no_verificable"
  }},
  "analisis_estructurado": {{
    "verificacion_documental": {{
      "paciente_coincide": true,
      "firma_sello_medico": true,
      "legibilidad_ocr_score": 95,
      "detalles": "..."
    }},
    "analisis_clinico": {{
      "diagnostico_cie10": "...",
      "congruencia_procedimiento": true,
      "hallazgos_preexistencia_detectados": false,
      "detalles": "..."
    }},
    "analisis_cobertura_y_ley": {{
      "carencia_aplicable": true,
      "carencia_superada": false,
      "emergencia_vital_exonerada": true,
      "sustento_legal_aplicado": "...",
      "detalles": "..."
    }}
  }},
  "score_confianza": 95,
  "clausulas_relevantes": ["..."],
  "documentos_faltantes": [],
  "recomendaciones": "..."
}}
```
"""
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parsea la respuesta de Gemini a un diccionario"""
        try:
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            
            return json.loads(clean_text.strip())
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] Error parseando respuesta JSON: {e}")
            return {
                "aprobado": False,
                "score_confianza": 0,
                "clausulas_relevantes": [],
                "documentos_faltantes": ["Error de parseo del modelo"],
                "recomendaciones": "Revision manual requerida"
            }

# Singleton
ai_agent = AIAgent()
