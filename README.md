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
| Servicio  | URL |
|-----------|-----|
| Frontend  | https://frontend-fallas-xxx-uc.a.run.app |
| Backend   | https://backend-fallas-26134329034.us-central1.run.app |
| MCP Server| https://mcp-mantenimiento-pl3bqyhpiq-wn.a.run.app |
| Docs API  | https://backend-fallas-26134329034.us-central1.run.app/docs |

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

## Pruebas de integración — Resultados

| # | Escenario | Tools invocadas | Resultado |
|---|-----------|-----------------|-----------|
| 1 | Reporte falla completo EQA-1001 | 4 tools + PDF | ✅ |
| 2 | Consulta normativa DS 081 | consultar_normativas | ✅ |
| 3 | Contexto conversacional EQA-1003 | integrar_datos | ✅ |
| 4 | Fuera de dominio | 0 tools | ✅ |
| 5 | Equipo no encontrado EQA-9999 | integrar_datos | ✅ |
| 6 | Swagger UI documentación | N/A | ✅ |
| 7 | Smoke tests automatizados 3/3 | N/A | ✅ |

## Arquitectura desplegada

- **Frontend**: Streamlit en Cloud Run us-central1
- **Backend**: FastAPI + LangChain ReAct en Cloud Run us-central1
- **RAG**: Elasticsearch 8.19 en GCP VM us-west4-a (2,665 chunks)
- **MCP Server**: FastMCP en Cloud Run us-west4
- **LLM**: GPT-4o (OpenAI)
- **Embeddings**: text-embedding-3-large (OpenAI)

## Estructura del repositorio
(ver árbol de carpetas en docs/arquitectura.md)