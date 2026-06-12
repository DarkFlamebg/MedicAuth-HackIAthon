### 📁 Estructura del Proyecto Optimizada

```
auth-ai/
├── frontend/                    # Vite + React + TypeScript
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard/
│   │   │   │   ├── AuthorizationCard.tsx
│   │   │   │   ├── MetricsPanel.tsx
│   │   │   │   ├── RealtimeUpdates.tsx
│   │   │   │   └── DecisionFlow.tsx
│   │   │   ├── Patient/
│   │   │   │   ├── PatientInfo.tsx
│   │   │   │   └── MedicalHistory.tsx
│   │   │   └── ui/              # shadcn/ui
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   └── websocket.ts     # Para updates en tiempo real
│   │   ├── hooks/
│   │   │   ├── useAuthorizations.ts
│   │   │   └── useRealtimeUpdates.ts
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   └── AuthorizationDetail.tsx
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── backend/                     # Python (FastAPI)
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── webhook.py
│   │   │   │   ├── authorization.py
│   │   │   │   └── health.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── services/
│   │   │   ├── ai_agent.py           # Agente principal
│   │   │   ├── notion_service.py     # Cliente Notion
│   │   │   ├── document_analyzer.py  # Análisis de PDF
│   │   │   ├── policy_matcher.py     # RAG para pólizas
│   │   │   └── decision_engine.py    # Lógica de autorización
│   │   ├── models/
│   │   │   ├── authorization.py
│   │   │   ├── patient.py
│   │   │   └── policy.py
│   │   ├── utils/
│   │   │   ├── validators.py
│   │   │   ├── parsers.py
│   │   │   └── pdf_extractor.py
│   │   └── main.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── docs/
│   ├── AI_TOOLS_USED.pdf
│   ├── ARCHITECTURE.md
│   └── DEMO_SCRIPT.md
│
├── .gitignore
└── README.md
```

### 🛠️ Stack Tecnológico

**Frontend (Vite + React):**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    "@tanstack/react-query": "^5.28.0",
    "axios": "^1.6.7",
    "recharts": "^2.12.0",
    "lucide-react": "^0.344.0",
    "react-hot-toast": "^2.4.1",
    "date-fns": "^3.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.1.4",
    "tailwindcss": "^3.4.1",
    "typescript": "^5.3.3"
  }
}
```

**Backend (Python):**
```txt
# Core Framework
fastapi==0.110.0
uvicorn[standard]==0.27.1
python-dotenv==1.0.1

# AI & ML
anthropic==0.18.1              # Claude API
openai==1.12.0                 # Para embeddings (RAG)
langchain==0.1.9               # Orquestación de agentes
langchain-community==0.0.24
chromadb==0.4.22               # Vector DB para RAG

# Notion & APIs
notion-client==2.2.1
requests==2.31.0
httpx==0.27.0

# Document Processing
pypdf==4.0.1                   # Extracción de PDF
python-multipart==0.0.9        # Upload de archivos
pillow==10.2.0                 # Procesamiento de imágenes

# Data & Validation
pydantic==2.6.1
pydantic-settings==2.1.0

# Utils
python-dateutil==2.8.2
```

### 🤖 Agente de IA - Arquitectura del Decision Engine

```python
# backend/app/services/ai_agent.py

"""
Agente Multi-Step para Autorización Quirúrgica

Pasos del Agente:
1. Extracción de Información del Informe Médico
2. Validación de Póliza (RAG)
3. Verificación de Requisitos de Carencia
4. Análisis de Cobertura
5. Decisión Final con Explicación
"""
```

### 📊 Flujo de Datos en Tiempo Real

```
┌─────────────────┐
│  Notion DB      │
│  (Trigger)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Webhook        │─────▶│  AI Agent        │
│  (FastAPI)      │      │  - Extract Info  │
└─────────────────┘      │  - RAG Search    │
                         │  - Validate      │
                         │  - Decide        │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Update Notion   │
                         │  + WebSocket     │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  React Dashboard │
                         │  (Real-time UI)  │
                         └──────────────────┘
```
```
┌──────────────────────────────────────────────────────────┐
│  1. Hospital crea nueva solicitud en Notion              │
│     (llena formulario: paciente, cirugía, póliza)        │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  2. Notion dispara webhook a tu backend                  │
│     POST https://tu-api.railway.app/webhook/notion       │
│     Body: { page_id, database_id, properties... }        │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  3. Backend Python recibe evento                         │
│     - Extrae datos de la solicitud                       │
│     - Descarga informe médico PDF de Notion              │
│     - Busca póliza relacionada                           │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  4. Agente IA procesa (Claude + RAG)                     │
│     - Analiza informe médico                             │
│     - Valida cobertura en póliza                         │
│     - Verifica carencia                                  │
│     - Genera decisión + explicación                      │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  5. Backend actualiza Notion                             │
│     - Estado: "Aprobado" / "Rechazado"                   │
│     - Razonamiento completo                              │
│     - Score de confianza                                 │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  6. Dashboard React muestra actualización en tiempo real │
│     (vía polling o WebSocket)                            │
└──────────────────────────────────────────────────────────┘
```

### 🎯 Features Diferenciadores

1. **Multi-Agent System**
   - Agente Extractor (analiza informe médico)
   - Agente Validador (verifica póliza con RAG)
   - Agente Decisor (emite veredicto final)

2. **RAG (Retrieval Augmented Generation)**
   - Embeddings de todas las pólizas en ChromaDB
   - Búsqueda semántica de coberturas
   - Citación de cláusulas específicas

3. **Dashboard Interactivo**
   - Visualización del "pensamiento" del agente
   - Métricas en tiempo real
   - Histórico de decisiones

4. **Explicabilidad Total**
   - Cada decisión viene con:
     - Razonamiento paso a paso
     - Referencias a cláusulas
     - Score de confianza (0-100%)
     - Documentos faltantes (si aplica)

### 🚀 Plan de Implementación (3 días)

**DÍA 1 - Setup & Backend Core:**
- ✅ Estructura del proyecto
- ✅ FastAPI + endpoints básicos
- ✅ Integración con Notion API
- ✅ Claude API setup
- ✅ Webhook funcionando
- ✅ Enfocar en funcionalidad y flujo antes que en diseño visual

**DÍA 2 - Agente IA & Frontend:**
- ✅ Implementar agente multi-step
- ✅ RAG con ChromaDB
- ✅ Dashboard React con Vite
- ✅ Integración frontend-backend
- ✅ WebSockets para tiempo real

**DÍA 3 - Polish & Deploy:**
- ✅ UI/UX refinamiento
- ✅ Testing con casos reales
- ✅ Video demo (3 min)
- ✅ Documentación PDF
- ✅ Deploy (Railway + Vercel)
- ✅ README épico

---
