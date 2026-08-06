# Sistema de Gestión de Fallas de Mantenimiento
## Proyecto Final — IA Generativa · Hidrocarburos del Perú

Aplicación end-to-end que utiliza IA Generativa para gestionar
fallas de mantenimiento industrial. El operador reporta una falla
en lenguaje natural y el sistema genera una orden de trabajo
estructurada respaldada por evidencia del historial SAP y
normativas públicas del sector de hidrocarburos.

## Arquitectura
- **Frontend**: Streamlit (Google Cloud Run)
- **Backend**: FastAPI + LangChain ReAct (Google Cloud Run)
- **RAG**: Elasticsearch — historial SAP + normativas DS 062/042
- **MCP Server**: FastMCP con tools de mantenimiento (Google Cloud Run)
- **LLM**: GPT-4o (OpenAI)

## URLs desplegadas
- Frontend: (pendiente)
- Backend API: (pendiente)
- MCP Server: https://mcp-mantenimiento-...run.app

## Módulos reutilizados
- M2: Agente LangChain de fallas de mantenimiento
- M4: Pipeline RAG con Elasticsearch
- M6: Servidor MCP desplegado en Cloud Run

## Variables de entorno
Ver `.env.example` para la lista completa de variables necesarias.

## Ejecución local
```bash
# 1. Clonar el repositorio
git clone https://github.com/TU-USUARIO/sistema-fallas-hidrocarburos.git

# 2. Copiar variables de entorno
cp .env.example .env
# Editar .env con los valores reales

# 3. Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# 4. Frontend (en otra terminal)
cd frontend && streamlit run app.py
```

## Estructura del repositorio
(ver árbol de carpetas en docs/arquitectura.md)