# MedicAuth AI - Backend Quirúrgico

Servicio de pre-autorización quirúrgica en tiempo real impulsado por Inteligencia Artificial y completamente integrado con Notion. Este backend actúa como un auditor forense ultra-preciso adaptado a la legislación y realidad clínica del sistema de salud ecuatoriano.

## 🚀 Arquitectura y Decisiones de Diseño

El sistema está diseñado bajo una arquitectura de alto rendimiento y máxima rigurosidad, enfocada en resolver las tres brechas críticas del uso de Modelos de Lenguaje (LLMs) en salud: alucinaciones clínicas, inconsistencia documental (OCR) y fallos de formato en API.

```
                  ┌───────────────────────────────┐
                  │      Notion Webhook Trigger   │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │   Agente 1: Auditor Forense  │ (Actor - Temp 0.1)
                  └───────────────┬───────────────┘
                                  │ Draft JSON
                                  ▼
                  ┌───────────────────────────────┐
                  │   Agente 2: Director Médico   │ (Critic - Temp 0.0)
                  └───────────────┬───────────────┘
                                  │ Veredicto Final
                                  ▼
                  ┌───────────────────────────────┐
                  │   Failsafe UTF-16 (Notion)    │ (Slicing 1900 chars)
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │      Actualización Notion     │ (Estado, Score, Reporte)
                  └───────────────────────────────┘
```

### 1. Motor Cognitivo Actor-Critic (Multi-Agente)
En lugar de depender de una sola llamada genérica a la IA, el backend implementa una **Arquitectura en Cascada de Doble Agente**:
*   **Agente 1: Auditor Forense (Actor)**: Diseñado para la extracción del informe médico (OCR), cálculo de carencias y estructuración de la póliza contratada. Trabaja a una temperatura de `0.1` para forzar consistencia sintáctica.
*   **Agente 2: Director Médico Revisor (Critic)**: Analiza el borrador del Agente 1, contrastándolo con el PDF médico original y las cláusulas de exclusión. Su único fin es desafiar y autocorregir la propuesta para evitar fraudes, omisiones o alucinaciones clínicas. Corre a temperatura `0.0` para una rigurosidad algorítmica absoluta.

### 2. Procesamiento Nativo de PDFs
Para garantizar la viabilidad en servidores en la nube sin sobrecargar de dependencias del sistema (como Poppler o Tesseract OCR local), el backend descarga los archivos desde el S3 seguro de Notion y envía los **bytes crudos del PDF directamente a la API de Gemini 2.5 Flash**, aprovechando su potente motor multimodal nativo para la interpretación de manuscritos clínicos y firmas.

### 3. Segmentación del Sistema de Salud Ecuatoriano
El motor cognitivo audita las solicitudes bifurcando las reglas de negocio en función del tipo de seguro:
*   **IESS / Seguridad Social**: Verificación obligatoria contra la *Cartera de Servicios del IESS (Resolución CD 559-2016)* y validación de cobertura de emergencias frente a bloqueos patronales.
*   **Medicina Prepagada**: Aplicación del marco de la *Ley 2000-4*, coberturas mínimas de hospitalización obligatoria y cálculo de penalizaciones por clínicas fuera de la red de prestadores.
*   **Seguros Privados**: Control estricto de reembolsos vs. pago directo, topes anuales, sublímites de eventos y validación del panel médico contratado.

### 4. Niveles de Complejidad MSP y Taxonomía Hospitalaria
El agente comprende la **Taxonomía de Niveles del Ministerio de Salud Pública de Ecuador (Nivel 1, 2 y 3)**. Cruza la complejidad del procedimiento quirúrgico (ej. colecistectomía vs. neurocirugía) con la capacidad instalada del hospital donde se solicita (ej. clínicas básicas vs. clínicas de referencia como Kennedy, Metropolitano, Alcívar o SOLCA).

### 5. Detección de Fraude y Abuso de Cobertura
El agente actúa como un detective forense buscando anomalías comunes:
*   **Fraude Documental**: Detección de firmas falsas, informes emitidos posteriormente al reclamo o sellos médicos sin número de registro profesional de la **SENESCYT** visible.
*   **Fraude Clínico**: Identificación del patrón de "emergencias simuladas" (procedimientos electivos planificados con meses de evolución que se ingresan como emergencias vitales para evadir periodos de carencia).
*   **Preexistencias Epidemiológicas**: Auditoría activa de patologías de alta litigiosidad en Ecuador (Colelitiasis, Hernias, Miomatosis uterina, Diabetes Tipo 2) buscando indicios en la anamnesis previos a la vigencia de la póliza.

### 6. Tarifario de Referencia Nacional (Anti-Sobrefacturación)
Valida el costo estimado de los procedimientos quirúrgicos contra un rango de precios referenciales de clínicas ecuatorianas privadas. Si el cobro solicitado supera el **150% del valor normal**, se reporta una alerta automática por sobrecosto para auditoría manual.

### 7. Prevención del Bug de Longitud UTF-16 (Notion API Failsafe)
La API de Notion restringe los campos de texto `rich_text` a exactamente **2000 caracteres**. Sin embargo, los emojis (como 🚨, 📋, ✅) ocupan **2 caracteres en UTF-16 (pares subrogados)** en los sistemas de Notion, mientras que en Python cuentan como 1. 
Para evitar fallos de validación HTTP 400 por desbordamiento de caracteres, el backend realiza un **corte dinámico a 1900 caracteres** en Python para todas las respuestas enviadas a Notion, blindando el canal contra caídas inesperadas en producción.

---

## 🛠️ Tecnologías Utilizadas

*   **FastAPI**: Framework de alto rendimiento y baja latencia para el desarrollo de la API.
*   **Google Gemini SDK**: Integración directa con `gemini-2.5-flash` para razonamiento multimodal.
*   **Notion SDK**: Conector oficial de Notion para consultas y actualizaciones en tiempo real.
*   **Pydantic v2**: Validación estricta y tipado estático de esquemas de datos.
*   **HTTPX**: Cliente asíncrono para descarga paralela de informes médicos.

---

## ⚙️ Configuración y Despliegue

### 1. Variables de Entorno (`.env`)
Crea un archivo `.env` en la raíz del backend con los siguientes tokens:
```env
NOTION_TOKEN=secret_yourNotionIntegrationToken
NOTION_SOLICITUDES_DB_ID=yourSolicitudesDatabaseID
NOTION_POLIZAS_DB_ID=yourPolizasDatabaseID
GEMINI_API_KEY=yourGoogleGeminiApiKey
```

### 2. Instalación de Dependencias
```bash
# Crear entorno virtual
python -m venv venv311
venv311\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Ejecución en Servidor de Desarrollo
```bash
uvicorn app.main:app --reload
```
El servidor levantará en `http://127.0.0.1:8000`.