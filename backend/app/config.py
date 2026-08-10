# ================================================================
# config.py — Configuración centralizada del backend
# Todas las variables de entorno en un solo lugar
# ================================================================
import os

# ── LLM ──────────────────────────────────────────────────────────
OPENAI_API_KEY  = os.environ.get("OPENAI_API_KEY", "")
LLM_MODEL       = os.environ.get("LLM_MODEL", "gpt-4o")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0"))

# ── Elasticsearch ─────────────────────────────────────────────────
ES_URL      = os.environ.get("ES_URL",      "http://34.125.122.137:9200")
ES_USER     = os.environ.get("ES_USER",     "elastic")
ES_PASSWORD = os.environ.get("ES_PASSWORD", "")
INDEX_NAME  = os.environ.get("INDEX_NAME",  "rag_fallas_pf_v1")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-large")
RAG_TOP_K   = int(os.environ.get("RAG_TOP_K", "4"))
RAG_SCORE_MIN = float(os.environ.get("RAG_SCORE_MIN", "0.65"))

# ── CSV ────────────────────────────────────────────────────────────
CSV_EQUIPOS   = os.environ.get("CSV_EQUIPOS",   "/app/data/equipos.csv")
CSV_REPUESTOS = os.environ.get("CSV_REPUESTOS", "/app/data/repuestos.csv")

# ── PDF ────────────────────────────────────────────────────────────
PDF_OUTPUT_DIR = os.environ.get("PDF_OUTPUT_DIR", "/tmp/ordenes_generadas")

# ── LangSmith ─────────────────────────────────────────────────────
LANGCHAIN_TRACING_V2 = os.environ.get("LANGCHAIN_TRACING_V2", "false")
LANGCHAIN_API_KEY    = os.environ.get("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT    = os.environ.get("LANGCHAIN_PROJECT", "fallas-hidrocarburos-pf")

# ── Servidor ──────────────────────────────────────────────────────
PORT    = int(os.environ.get("PORT", "8000"))
VERSION = "1.0.0"

# Aplicar variables al entorno de Python
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
if LANGCHAIN_TRACING_V2 == "true" and LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"]    = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"]    = LANGCHAIN_PROJECT
