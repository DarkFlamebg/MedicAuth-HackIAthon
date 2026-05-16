# 🏥 SurgeryAuth AI - Backend

API Backend para el agente inteligente de pre-autorización quirúrgica en tiempo real.

## 🚀 Stack Tecnológico

- **FastAPI** - Framework web moderno y rápido
- **Python 3.11+** - Lenguaje de programación
- **Anthropic Claude** - Agente de IA para análisis
- **Notion API** - Base de datos colaborativa
- **ChromaDB** - Vector database para RAG (futuro)

## 📁 Estructura del Proyecto

```
backend/
├── app/
│   ├── api/
│   │   └── routes/          # Endpoints de la API
│   │       ├── webhook.py   # Webhook de Notion
│   │       ├── authorization.py
│   │       └── health.py
│   ├── core/
│   │   └── config.py        # Configuración y variables de entorno
│   ├── models/
│   │   └── authorization.py # Modelos Pydantic
│   ├── services/
│   │   ├── notion_service.py  # Cliente Notion
│   │   └── ai_agent.py        # Agente de IA
│   ├── utils/               # Utilidades
│   └── main.py              # Punto de entrada
├── requirements.txt
├── .env.example
└── README.md
```

## ⚙️ Configuración

### 1. Clonar el repositorio

```bash
git clone <tu-repo>
cd surgery-auth-ai/backend
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Activar en Linux/Mac
source venv/bin/activate

# Activar en Windows
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```


#### 🔑 Cómo obtener las credenciales:

**Notion:**
1. Ve a https://www.notion.so/my-integrations
2. Crea una nueva integración
3. Copia el token (Internal Integration Token)
4. Crea tus databases y compártelas con la integración
5. Copia los IDs de las databases desde la URL

**Anthropic (Claude):**
1. Ve a https://console.anthropic.com/
2. Genera un API key
3. Cópialo en `ANTHROPIC_API_KEY`

## 🏃 Ejecutar el Servidor

### Modo desarrollo (con auto-reload)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Modo producción

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

El servidor estará disponible en:
- API: http://localhost:8000
- Documentación interactiva: http://localhost:8000/docs
- Documentación alternativa: http://localhost:8000/redoc


## 🔄 Flujo de Procesamiento

1. **Webhook recibe evento** de Notion cuando se crea una solicitud
2. **Extrae datos** de la solicitud y busca la póliza relacionada
3. **Agente IA analiza** con Claude:
   - Valida cobertura
   - Verifica período de carencia
   - Analiza informe médico
   - Genera decisión con explicación
4. **Actualiza Notion** con la decisión y razonamiento
5. **Frontend recibe** actualización en tiempo real

## 🚀 Deploy

### Railway (Recomendado)

1. Instalar Railway CLI:
```bash
npm i -g @railway/cli
```

2. Login:
```bash
railway login
```

3. Deploy:
```bash
railway up
```

4. Configurar variables de entorno en el dashboard de Railway

### Render

1. Conectar repositorio en render.com
2. Configurar como "Web Service"
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## 📝 Notas Importantes

- El webhook de Notion requiere HTTPS en producción
- Railway y Render proveen HTTPS automáticamente
- Asegúrate de configurar las variables de entorno en producción

## 🐛 Troubleshooting

### Error: "NOTION_TOKEN not found"
- Verifica que el archivo `.env` existe
- Asegúrate de que las variables están configuradas correctamente

### Error: "Database not found"
- Verifica que compartiste la database con la integración
- Confirma que los IDs son correctos

### Error al conectar con Claude
- Verifica tu API key de Anthropic
- Revisa límites de rate en tu cuenta

## 📚 Recursos

- [Documentación de FastAPI](https://fastapi.tiangolo.com/)
- [Notion API Docs](https://developers.notion.com/)
- [Anthropic Claude Docs](https://docs.anthropic.com/)


### Alternativa: Notion + DB Tradicional (Híbrido)
Si quieres lo mejor de ambos mundos:
```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Notion    │────────▶│   Backend    │────────▶│  PostgreSQL │
│  (Interface)│ webhook │   (FastAPI)  │  sync   │  (Rápido)   │
└─────────────┘         └──────────────┘         └─────────────┘
     ▲                          │
     │                          │
     └──────────────────────────┘
           Actualización
```
## Ventajas:

 - Notion como interfaz visual para jueces
 - PostgreSQL para queries rápidas y complejas
 - Sincronización bidireccional

Pero para el hackathon, SOLO Notion es suficiente (y más impresionante porque no requiere infraestructura extra).