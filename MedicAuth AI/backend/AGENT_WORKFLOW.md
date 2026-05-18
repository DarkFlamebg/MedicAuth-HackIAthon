# Arquitectura y Flujo de Trabajo: Agente de IA "MedicAuth"

Este documento describe el funcionamiento interno del backend y el agente de Inteligencia Artificial desarrollado para el hackathon. Está diseñado para facilitar la comprensión del ciclo de vida de una solicitud de autorización quirúrgica y servir como base para la generación de diagramas arquitectónicos.

## 🔄 Flujo de Ejecución (Paso a Paso)

El sistema opera bajo un flujo asíncrono y en segundo plano (Background Tasks) para asegurar tiempos de respuesta rápidos y evitar bloqueos en el servidor.

### 1. Trigger (Disparador)
- **Actor:** Frontend, Usuario (vía Swagger/Postman) o Webhook de automatización (Zapier/Make).
- **Acción:** Se envía una petición `POST` al endpoint `/api/webhook/notion` (o `/api/webhook/notion/from-url`).
- **Payload:** El ID único de la página de la solicitud en Notion (`page_id`).
- **Respuesta Inmediata:** FastAPI responde con un `200 OK` (Accepted) casi instantáneamente, mientras que el análisis pesado se delega a una Background Task.

### 2. Extracción de Datos y Contexto (Notion API)
- **Extracción de Solicitud:** El backend se conecta a la Base de Datos "Solicitudes de Autorización" en Notion usando el `AsyncClient` de `notion-client` y extrae los datos clínicos y demográficos del paciente (Edad, Cédula, Tipo de Cirugía, Hospital, Médico Tratante).
- **Resolución de Póliza:** A través de una relación de base de datos en Notion, el sistema identifica el ID de la póliza asociada e interactúa con la Base de Datos "Pólizas de Seguros" para extraer los términos del contrato: Coberturas, Exclusiones, Tipo de Plan y Días de Carencia.
- **Validación de Integridad:** Si hay celdas vacías, el sistema las maneja de forma segura. Si no existe póliza, el sistema detiene el flujo y actualiza el estado a "Documentos Faltantes".

### 3. Extracción Documental (Procesamiento de PDF)
- El sistema identifica el archivo adjunto (Informe Médico en PDF) en la página de Notion.
- Utiliza `httpx` para descargar de forma segura el PDF directamente a la memoria RAM (bytes) sin almacenar archivos basura en el disco del servidor.

### 4. Análisis Cognitivo (Agente IA - Gemini)
- **Motor:** Se utiliza el modelo multimodal `gemini-2.5-flash` de Google.
- **Arquitectura de Prompting:** Se implementa un diseño **Self-Reflective (Auto-reflexivo)** de alta eficiencia, donde en un solo ciclo la IA hace el papel de Auditor Médico y Analista de Seguros.
- **Input:** Se envía al modelo un mega-prompt estructurado que contiene:
  1. Los datos extraídos del paciente y la solicitud.
  2. Las reglas de negocio de la póliza (coberturas y exclusiones).
  3. El archivo PDF (bytes) inyectado de forma nativa como `application/pdf`.
- **Análisis:** La IA contrasta la solicitud médica contra el texto del PDF y las cláusulas del seguro, validando preexistencias, periodos de carencia y necesidad médica.
- **Output (Estructurado):** La IA devuelve exclusivamente un objeto JSON validado con:
  - `aprobado` (booleano).
  - `razonamiento` (justificación clínica/administrativa).
  - `score_confianza` (0-100%).
  - `clausulas_relevantes` y `documentos_faltantes` (en caso de rechazo o suspensión).

### 5. Actualización y Cierre del Ciclo (Notion API)
- El sistema toma el JSON generado por la IA y calcula el estado final (`Aprobado`, `Rechazado`, o `Documentos Faltantes`).
- Se realiza una petición de actualización (PATCH) a la página de Notion del paciente.
- Se sobrescriben las celdas de "Estado", "Decisión IA", "Razonamiento", "Score de Confianza" y "Tiempo de Procesamiento".
- **Fin del proceso:** La página de Notion se actualiza en tiempo real frente a los ojos del usuario. Todo el ciclo toma un promedio de **20 a 30 segundos**.

---

## 🛠️ Stack Tecnológico Involucrado
- **Framework Core:** FastAPI (Python) + Uvicorn
- **Gestión de Tareas:** FastAPI BackgroundTasks (Procesamiento Asíncrono no bloqueante)
- **Integración de Datos:** Notion API (`notion-client` Async)
- **Motor de IA:** Google Generative AI (`gemini-2.5-flash`)
- **Despliegue:** Render (Web Service)

---

## 💡 Prompt para generar el Diagrama
*(Copia y pega esto en otra IA para generar el diagrama visual)*

> "Basado en el documento 'Arquitectura y Flujo de Trabajo: Agente de IA MedicAuth', genérame un código de diagrama de secuencia usando sintaxis **Mermaid**. Quiero que los actores principales sean: 'Frontend/Webhook', 'FastAPI Backend', 'Notion API (Solicitudes y Pólizas)' y 'Google Gemini IA'. Asegúrate de mostrar la Background Task como una bifurcación asíncrona después de devolver el 200 OK, y detalla el envío del PDF en bytes hacia Gemini."
