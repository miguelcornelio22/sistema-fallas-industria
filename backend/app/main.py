# ================================================================
# main.py — FastAPI app del backend
# Proyecto Final — Sistema de Gestión de Fallas
# Hidrocarburos del Perú
# ================================================================
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import VERSION
from app.routes.consulta import router
from app.services.agente import inicializar_agente

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
log = logging.getLogger("backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa el agente al arrancar y limpia al apagar."""
    log.info("=== Backend arrancando ===")
    try:
        inicializar_agente()
        log.info("=== Agente inicializado — Backend listo ===")
    except Exception as e:
        log.error(f"Error inicializando agente: {e}")
        raise
    yield
    log.info("=== Backend apagándose ===")


# ── Crear la app ──────────────────────────────────────────────────
app = FastAPI(
    title="Sistema de Gestión de Fallas — Hidrocarburos del Perú",
    description=(
        "Backend del proyecto final de IA Generativa. "
        "Agente ReAct con RAG sobre normativas y herramientas MCP "
        "para gestión de fallas de mantenimiento industrial."
    ),
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — permite conexión desde el frontend Streamlit ──────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Registrar rutas ───────────────────────────────────────────────
app.include_router(router)


# ── Ruta raíz ─────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "sistema": "Gestión de Fallas — Hidrocarburos del Perú",
        "version": VERSION,
        "endpoints": {
            "consulta": "POST /consulta",
            "health":   "GET  /health",
            "docs":     "GET  /docs",
        }
    }
