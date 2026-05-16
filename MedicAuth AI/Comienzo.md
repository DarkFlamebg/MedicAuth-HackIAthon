
## 🎯 Propuesta de Solución
### 🏗️ Arquitectura Propuesta

```
┌─────────────────┐       ┌──────────────────┐      ┌─────────────────┐
│  Notion DB      │─────▶│   AI Agent       │─────▶│  Dashboard      │
│  (Hospitales +  │       │   (Claude/GPT)   │      │  (React/Vite)│
│  Aseguradoras)  │       │   + RAG          │      │                 │
└─────────────────┘       └──────────────────┘      └─────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Webhook/API     │
                         │  Real-time       │
                         └──────────────────┘
```

### 🛠️ Stack Tecnológico

**Frontend:**
- **Vite + React + TypeScript** - MVP rápido y ligero
- **Tailwind CSS** - UI funcional y ágil
- **Notion API** - Base de datos colaborativa

**IA & Automatización:**
- **Anthropic Claude** (via API) - Para análisis de documentos médicos
- **LangChain** - Para orquestar el agente
- **Vercel AI SDK** - Para streaming de respuestas
- **OpenAI Embeddings** - Para RAG (búsqueda semántica en pólizas)

**Base de Datos:**
- **Notion** - Como DB principal
- **Upstash Redis** - Para cache y rate limiting

### Flujo
[ Cliente React ] 
       │ (HTTP / WebSockets)
       ▼
[ Backend FastAPI ] ───► [ Base de Datos Real: PostgreSQL / MongoDB ] (Datos de la App)
       │
       ▼ (Asíncrono / Background Tasks)
[ API de Notion ] (Solo para reportes, respaldos o lecturas de contenido estático)

### 🎨 Diferenciadores Clave (no será un chatbot común)

1. **Dashboard Interactivo en Tiempo Real**
   - Visualización de autorizaciones pendientes
   - Métricas en tiempo real (tiempo de respuesta, % de aprobación)
   - Flujo visual del proceso de decisión de la IA

2. **Agente Multi-Step Reasoning**
   - No solo responde, sino que muestra su razonamiento paso a paso
   - Extrae información de pólizas con RAG
   - Valida contra reglas de negocio automáticamente

3. **Webhook Automation**
   - Cuando se crea un registro en Notion → trigger automático
   - Notificaciones en tiempo real
   - Actualización automática del estado

4. **Explicabilidad**
   - Muestra por qué aprobó/rechazó
   - Referencias a cláusulas específicas de la póliza
   - Score de confianza

### 📋 Base de Datos en Notion (Estructura)

**Tabla 1: Solicitudes de Autorización**
```
- ID Solicitud
- Paciente (nombre, cédula, edad)
- Número de Póliza
- Tipo de Cirugía
- Fecha Solicitada
- Hospital
- Médico Tratante
- Informe Médico (archivo PDF/texto)
- Estado (Pendiente/Aprobado/Rechazado/Documentos Faltantes)
- Decisión IA (JSON con razonamiento)
- Fecha de Respuesta
```

**Tabla 2: Pólizas de Seguros**
```
- Número de Póliza
- Aseguradora
- Tipo de Plan
- Coberturas (JSON)
- Exclusiones
- Período de Carencia
- Estado (Activa/Suspendida)
```

### 🚀 Plan de Desarrollo (3 días)

> Prioridad: funcionalidad antes que apariencia. El MVP debe funcionar bien primero.

**Día 1 (Hoy):**
- ✅ Definir arquitectura
- Setup del proyecto Vite + React
- Configurar Notion API
- Crear estructura de BD en Notion
- Setup Claude API
- Webhook básico funcionando

**Día 2:**
- Desarrollar el agente de IA con lógica de autorización
- Implementar RAG para búsqueda en pólizas
- Dashboard con visualización de solicitudes
- Testing con casos reales

**Día 3:**
- Pulir UI/UX
- Video demo (máx 3 min)
- Documentación PDF de herramientas IA
- Deploy a producción
- README completo en GitHub

### 🎬 Demo Video (3 min) - Guión

```
00:00-00:30 → Problema: mostrar proceso manual actual
00:30-01:00 → Solución: presentar SurgeryAuth AI
01:00-02:00 → Demo en vivo:
              - Crear solicitud en Notion
              - Ver procesamiento en tiempo real
              - Mostrar decisión con explicación
02:00-02:45 → Impacto: métricas, beneficios
02:45-03:00 → Cierre y call to action
```



### Notion como Base de Datos
**¿Por qué Notion?**

 - Requisito del Hackathon: El documento dice explícitamente "una base de datos de Notion"
 - Interfaz Visual: Los jueces pueden ver los datos sin código
 - Colaborativo: Hospitales y aseguradoras pueden actualizar datos
 - Webhooks Nativos: Notion notifica cuando hay cambios
 -Sin infraestructura: No necesitas montar PostgreSQL/MongoDB

 