# ================================================================
# routes/consulta.py — Endpoints del backend
# POST /consulta  → invoca el agente con el reporte de falla
# GET  /health    → verifica el estado del backend
# ================================================================
import logging
import re
import os
import glob
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from app.services.agente import get_agente, get_vector_store
from app.config import VERSION, PDF_OUTPUT_DIR

log    = logging.getLogger("backend.routes")
router = APIRouter()


# ── Modelos de entrada y salida ───────────────────────────────────
class ConsultaRequest(BaseModel):
    session_id:  str
    mensaje:     str
    equipo_id:   Optional[str] = None


class FuenteRAG(BaseModel):
    source: str
    page:   int
    score:  float


class ConsultaResponse(BaseModel):
    respuesta:     str
    fuentes_rag:   list[FuenteRAG]
    tools_usadas:  list[str]
    session_id:    str
    orden_pdf:     Optional[str] = None


class HealthResponse(BaseModel):
    status:        str
    elasticsearch: str
    version:       str
    mensaje:       str


# ── Helpers ───────────────────────────────────────────────────────
def _extraer_fuentes(messages: list) -> list[FuenteRAG]:
    """Extrae las fuentes RAG de los mensajes del agente."""
    fuentes = []
    patron  = re.compile(
        r"\[(?:Fuente|Registro)\s+\d+\s*\|\s*Score:\s*([\d.]+)\s*\|"
        r"\s*Doc:\s*([^,]+),\s*Pag:\s*(\d+)\]",
        re.IGNORECASE
    )
    for msg in messages:
        contenido = ""
        if hasattr(msg, "content"):
            contenido = str(msg.content)
        elif hasattr(msg, "tool_call_id"):
            contenido = str(getattr(msg, "content", ""))

        for match in patron.finditer(contenido):
            try:
                fuentes.append(FuenteRAG(
                    score=float(match.group(1)),
                    source=match.group(2).strip(),
                    page=int(match.group(3)),
                ))
            except (ValueError, IndexError):
                pass

    # Deduplicar por source + page
    vistos = set()
    unicas = []
    for f in fuentes:
        key = (f.source, f.page)
        if key not in vistos:
            vistos.add(key)
            unicas.append(f)
    return sorted(unicas, key=lambda x: x.score, reverse=True)


def _extraer_tools_usadas(messages: list) -> list[str]:
    """Extrae los nombres de las tools invocadas por el agente."""
    tools = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                nombre = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                if nombre and nombre not in tools:
                    tools.append(nombre)
    return tools


def _obtener_ultimo_pdf() -> Optional[str]:
    """Obtiene el nombre del último PDF generado en esta sesión."""
    patron = os.path.join(PDF_OUTPUT_DIR, "Orden_N*.pdf")
    pdfs   = sorted(glob.glob(patron))
    if pdfs:
        return os.path.basename(pdfs[-1])
    return None


# ── ENDPOINT: POST /consulta ──────────────────────────────────────
@router.post("/consulta", response_model=ConsultaResponse)
async def consulta(request: ConsultaRequest):
    """
    Recibe un reporte de falla y devuelve el análisis del agente.
    El session_id mantiene el contexto conversacional entre llamadas.
    """
    if not request.mensaje or not request.mensaje.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    if len(request.mensaje) > 2000:
        raise HTTPException(
            status_code=400,
            detail="El mensaje excede el límite de 2000 caracteres."
        )

    log.info(f"[{request.session_id}] Consulta recibida: {request.mensaje[:80]}...")

    try:
        agente = get_agente()
        config = {"configurable": {"thread_id": request.session_id}}

        resultado = agente.invoke(
            {"messages": [HumanMessage(content=request.mensaje)]},
            config=config
        )

        messages      = resultado.get("messages", [])
        respuesta     = messages[-1].content if messages else "Sin respuesta del agente."
        fuentes_rag   = _extraer_fuentes(messages)
        tools_usadas  = _extraer_tools_usadas(messages)
        orden_pdf     = _obtener_ultimo_pdf()

        log.info(
            f"[{request.session_id}] Respuesta generada | "
            f"Tools: {tools_usadas} | Fuentes: {len(fuentes_rag)} | "
            f"PDF: {orden_pdf}"
        )

        return ConsultaResponse(
            respuesta=respuesta,
            fuentes_rag=fuentes_rag,
            tools_usadas=tools_usadas,
            session_id=request.session_id,
            orden_pdf=orden_pdf,
        )

    except RuntimeError as e:
        log.error(f"Error de runtime: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log.error(f"Error inesperado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ── ENDPOINT: GET /health ─────────────────────────────────────────
@router.get("/health", response_model=HealthResponse)
async def health():
    """
    Verifica el estado del backend y sus dependencias.
    Retorna 200 si todo está OK, 503 si hay algún problema.
    """
    es_status = "error"
    try:
        vs = get_vector_store()
        if vs is not None:
            count     = vs.client.count(index="rag_fallas_pf_v1")
            es_status = f"ok ({count['count']} chunks)"
    except Exception as e:
        es_status = f"error: {str(e)[:50]}"
        log.warning(f"Health check ES falló: {e}")

    status  = "ok" if "ok" in es_status else "degraded"
    mensaje = (
        "Backend operativo. Todos los servicios activos."
        if status == "ok"
        else "Backend activo pero Elasticsearch con problemas."
    )

    return HealthResponse(
        status=status,
        elasticsearch=es_status,
        version=VERSION,
        mensaje=mensaje,
    )
