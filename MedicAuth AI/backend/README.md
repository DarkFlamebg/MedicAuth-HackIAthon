---

# MedicAuth AI - Backend Quirúrgico

Servicio de pre-autorización quirúrgica en tiempo real impulsado por Inteligencia Artificial y completamente integrado con Notion. Este backend actúa como un auditor forense ultra-preciso adaptado a la legislación y realidad clínica del sistema de salud ecuatoriano.

## 🚀 Arquitectura y Decisiones de Diseño

El sistema está diseñado bajo una arquitectura de alto rendimiento y máxima rigurosidad, enfocada en resolver las tres brechas críticas del uso de Modelos de Lenguaje (LLMs) en salud: alucinaciones clínicas, inconsistencia documental (OCR) y fallos de formato en API.

```
                  ┌───────────────────────────────┐
                  │     Notion Webhook Trigger   │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │   Almacenamiento Cloudinary   │ (Generación de URL pública)
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │    Orquestador LangGraph      │ (Manejo de Estado / State)
                  └───────────────┬───────────────┘
                                  │
                                  ├──────────────────────────────┐
                                  ▼                              ▼
                  ┌───────────────────────────────┐ ┌───────────────────────────────┐
                  │  Agente 1: Auditor Forense    │ │ Agente 2: Director Médico     │
                  │   (Actor - Extracción OCR)    │ │    (Critic - Mitigación)      │
                  └───────────────────────────────┘ └───────────────────────────────┘
                                  │                              │
                                  └───────────────┬──────────────┘
                                                  │ Veredicto Unificado
                                                  ▼
                  ┌───────────────────────────────┐
                  │    Failsafe UTF-16 (Notion)   │ (Slicing 1900 chars)
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │     Actualización Notion      │ (Estado, Score, Reporte)
                  └───────────────────────────────┘

```

### 1. Orquestación Orientada a Estados con LangGraph (Multi-Agente)

En lugar de depender de llamadas lineales o prompts genéricos encadenados, el núcleo cognitivo está gobernado por un **grafo cíclico dirigido asíncrono (LangGraph)** que encapsula el estado global de la auditoría (`AuthorizationState`).

* **Agente 1: Auditor Forense (Actor)**: Ejecuta de forma asíncrona mediante un nodo del grafo la lectura e interpretación multimodal del informe médico mediante la URL segura de Cloudinary. Extrae carencias, estructuración y diagnóstico clínico a una temperatura de `0.1` para consistencia sintáctica.
* **Agente 2: Director Médico Revisor (Critic)**: Actúa como un nodo de evaluación de calidad y mitigación de alucinaciones. Contrasta la propuesta del Agente 1 con las condiciones de la póliza y las exclusiones de ley a temperatura `0.0`, realimentando al grafo si detecta incongruencias antes de consolidar el veredicto final.

### 2. Pipeline Multimodal Desacoplado (Cloudinary Gateway)

Para blindar el despliegue en entornos Serverless/PaaS como Render y evitar sobrecargar el sistema de archivos con la descarga de binarios o dependencias pesadas de OCR local (como Poppler o Tesseract), el backend delega la gestión de los informes médicos a un flujo optimizado:

1. El webhook recibe la carga útil desde Notion.
2. El archivo se procesa de forma segura mediante el gateway de **Cloudinary**, generando una URL pública estructurada y eliminando problemas de autenticación 401.
3. El nodo extractor de **LangGraph** consume dicha URL y utiliza la ventana de contexto y visión nativa de **Gemini 2.5 Flash** para procesar el documento directo desde la nube.

### 3. Segmentación del Sistema de Salud Ecuatoriano

El motor cognitivo audita las solicitudes bifurcando las reglas de negocio en función del tipo de seguro:

* **IESS / Seguridad Social**: Verificación obligatoria contra la *Cartera de Servicios del IESS (Resolución CD 559-2016)* y validación de cobertura de emergencias frente a bloqueos patronales.
* **Medicina Prepagada**: Aplicación del marco de la *Ley de Medicina Prepagada (Ley 2000-4)*, coberturas mínimas de hospitalización obligatoria y cálculo de penalizaciones por clínicas fuera de la red de prestadores.
* **Seguros Privados**: Control estricto de reembolsos vs. pago directo, topes anuales, sublímites de eventos y validación del panel médico contratado.

### 4. Niveles de Complejidad MSP y Taxonomía Hospitalaria

El agente comprende la **Taxonomía de Niveles del Ministerio de Salud Pública de Ecuador (Nivel 1, 2 y 3)**. Cruza la complejidad del procedimiento quirúrgico (ej. colecistectomía vs. neurocirugía) con la capacidad instalada del hospital donde se solicita (ej. clínicas básicas vs. clínicas de referencia como Kennedy, Metropolitano, Alcívar o SOLCA).

### 5. Detección de Fraude y Abuso de Cobertura

El agente actúa como un detective forense buscando anomalías comunes:

* **Fraude Documental**: Detección de firmas falsas, informes emitidos posteriormente al reclamo o sellos médicos sin número de registro profesional de la **SENESCYT** visible.
* **Fraude Clínico**: Identificación del patrón de "emergencias simuladas" (procedimientos electivos planificados con meses de evolución que se ingresan como emergencias vitales para evadir periodos de carencia).
* **Preexistencias Epidemiológicas**: Auditoría activa de patologías de alta litigiosidad en Ecuador (Colelitiasis, Hernias, Miomatosis uterina, Diabetes Tipo 2) buscando indicios en la anamnesis previos a la vigencia de la póliza.

### 6. Tarifario de Referencia Nacional (Anti-Sobrefacturación)

Valida el costo estimado de los procedimientos quirúrgicos contra un rango de precios referenciales de clínicas ecuatorianas privadas. Si el cobro solicitado supera el **150% del valor normal**, se reporta una alerta automática por sobrecosto para auditoría manual.

### 7. Prevención del Bug de Longitud UTF-16 (Notion API Failsafe)

La API de Notion restringe los campos de texto `rich_text` a exactamente **2000 caracteres**. Sin embargo, los emojis (como 🚨, 📋, ✅) ocupan **2 caracteres en UTF-16 (pares subrogados)** en los sistemas de Notion, mientras que en Python cuentan como 1.
Para evitar fallos de validación HTTP 400 por desbordamiento de caracteres, el backend realiza un **corte dinámico a 1900 caracteres** en Python para todas las respuestas enviadas a Notion, blindando el canal contra caídas inesperadas en producción.

---

## 🛠️ Tecnologías Utilizadas

* **FastAPI**: Framework de alto rendimiento y baja latencia para la exposición asíncrona de endpoints y webhooks.
* **LangGraph & LangChain**: Orquestador multi-agente basado en grafos de estado y conectores de IA.
* **Google Gemini SDK (`langchain-google-genai`)**: Integración directa con `gemini-2.5-flash` para razonamiento y lectura multimodal nativa.
* **Cloudinary**: Gateway de almacenamiento y optimización para servir los documentos médicos al agente.
* **Notion SDK (`notion-client`)**: Conector oficial de Notion para consultas transaccionales y actualizaciones en tiempo real.
* **Pydantic v2**: Validación estricta, tipado estático y parsing de esquemas de datos clínicos y respuestas de IA.
* **HTTPX**: Cliente HTTP asíncrono para comunicaciones eficientes entre microservicios.

---

## ⚙️ Configuración y Despliegue

### 1. Variables de Entorno (`.env`)

Crea un archivo `.env` en la raíz del backend con los siguientes tokens obligatorios:

```env
# Servidor y Entorno
PORT=8000
ENVIRONMENT=production

# Integración con Notion
NOTION_TOKEN=secret_yourNotionIntegrationToken
NOTION_SOLICITUDES_DB_ID=yourSolicitudesDatabaseID
NOTION_POLIZAS_DB_ID=yourPolizasDatabaseID

# Núcleo de Inteligencia Artificial
GEMINI_API_KEY=yourGoogleGeminiApiKey

# Proveedor de Almacenamiento Multimodal
CLOUDINARY_CLOUD_NAME=yourCloudName
CLOUDINARY_API_KEY=yourCloudinaryApiKey
CLOUDINARY_API_SECRET=yourCloudinaryApiSecret

```

> Copia este archivo como `.env` y completa tus credenciales antes de ejecutar la aplicación.

### 2. Instalación de Dependencias

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias con candados de estabilidad para Render
pip install -r requirements.txt

```

### 3. Ejecución en Servidor de Desarrollo

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

```

El servidor levantará localmente en `http://localhost:8000`. Puedes verificar la documentación interactiva en `/docs`.
