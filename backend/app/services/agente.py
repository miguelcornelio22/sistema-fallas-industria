# ================================================================
# services/agente.py — Lógica del agente LangChain
# Contiene las 4 tools y la creación del agente ReAct.
# Se inicializa una sola vez al arrancar el backend (singleton).
# ================================================================
import os
import uuid
import datetime
import logging

import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_elasticsearch import ElasticsearchStore
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from app.config import (
    ES_URL, ES_USER, ES_PASSWORD, INDEX_NAME, EMBED_MODEL,
    RAG_TOP_K, RAG_SCORE_MIN, CSV_EQUIPOS, CSV_REPUESTOS,
    PDF_OUTPUT_DIR, LLM_MODEL, LLM_TEMPERATURE,
)

log = logging.getLogger("backend.agente")

# ── Estado global del agente ──────────────────────────────────────
_agente      = None
_vector_store = None
_df_equipos  = None
_df_repuestos = None
_orden_contador = 0

SYSTEM_PROMPT = """Eres un asistente experto en gestion de fallas
de mantenimiento para Hidrocarburos del Peru (TGP).

DOMINIO: Fallas de equipos industriales, mantenimiento,
normativas DS 062, DS 081, DS 018, ASME B31.4, ASME B31.8.

HERRAMIENTAS — USARLAS SIEMPRE ANTES DE RESPONDER:
1. consultar_normativas: normativas y documentos tecnicos indexados
2. consultar_historial: historial de fallas SAP via RAG
3. integrar_datos: datos del equipo y repuestos desde CSV
4. generar_orden_trabajo: genera PDF — SIEMPRE llamar al final

FLUJO OBLIGATORIO PARA REPORTE DE FALLA:
Paso 1: integrar_datos(id_equipo) → extraer ubicacion, criticidad, stock
Paso 2: consultar_historial(descripcion de la falla)
Paso 3: consultar_normativas(tipo de falla y norma aplicable)
Paso 4: generar_orden_trabajo con TODOS los parametros:
  - id_equipo, reporte (SOLO la falla original del usuario),
  - criticidad y ubicacion (de integrar_datos),
  - nota_preventiva (de consultar_normativas),
  - historial_texto (de consultar_historial),
  - stock_repuesto y tiempo_reposicion (de integrar_datos)

REGLAS:
- Cita siempre fuente y pagina del RAG.
- Si no hay evidencia, dilo explicitamente. No inventes.
- Rechaza consultas fuera del dominio de mantenimiento industrial."""


def _init_vector_store():
    global _vector_store
    embeddings   = OpenAIEmbeddings(model=EMBED_MODEL)
    _vector_store = ElasticsearchStore(
        index_name=INDEX_NAME,
        embedding=embeddings,
        es_url=ES_URL,
        es_user=ES_USER,
        es_password=ES_PASSWORD,
    )
    log.info(f"Elasticsearch conectado: {ES_URL}/{INDEX_NAME}")


def _init_csv():
    global _df_equipos, _df_repuestos
    _df_equipos   = pd.read_csv(CSV_EQUIPOS,   sep=";", encoding="latin1")
    _df_repuestos = pd.read_csv(CSV_REPUESTOS, sep=";", encoding="latin1")
    log.info(f"CSV: {len(_df_equipos)} equipos, {len(_df_repuestos)} repuestos")


# ── TOOLS ─────────────────────────────────────────────────────────
@tool
def consultar_normativas(query: str) -> str:
    """Busca en el corpus de normativas y documentos tecnicos indexados.
    Incluye DS 062, DS 081, DS 018, ASME B31.4, ASME B31.8 e historial SAP.
    Args:
        query: pregunta o descripcion en texto libre.
    """
    if _vector_store is None:
        return "ERROR: Elasticsearch no inicializado."
    try:
        results   = _vector_store.similarity_search_with_score(query, k=RAG_TOP_K)
        filtrados = [(d, s) for d, s in results if s >= RAG_SCORE_MIN]
        if not filtrados:
            return "Sin evidencia en el corpus para esta consulta."
        partes = []
        for i, (doc, score) in enumerate(filtrados, 1):
            m = doc.metadata
            partes.append(
                f"[Fuente {i} | Score: {score:.3f} | "
                f"Doc: {m.get('doc_name','?')}, Pag: {m.get('page','?')}]\n"
                f"{doc.page_content[:500]}"
            )
        return "\n\n---\n\n".join(partes)
    except Exception as e:
        return f"ERROR RAG normativas: {str(e)}"


@tool
def consultar_historial(query: str) -> str:
    """Busca fallas similares en el historial SAP usando RAG semantico.
    Args:
        query: descripcion de la falla en texto libre.
    """
    if _vector_store is None:
        return "ERROR: Elasticsearch no inicializado."
    try:
        results   = _vector_store.similarity_search_with_score(query, k=RAG_TOP_K)
        filtrados = [(d, s) for d, s in results if s >= RAG_SCORE_MIN]
        if not filtrados:
            return "Sin registros similares en el historial SAP."
        partes = []
        for i, (doc, score) in enumerate(filtrados, 1):
            m = doc.metadata
            partes.append(
                f"[Registro {i} | Score: {score:.3f} | "
                f"Doc: {m.get('doc_name','?')}, Pag: {m.get('page','?')}]\n"
                f"{doc.page_content[:400]}"
            )
        return "\n\n---\n\n".join(partes)
    except Exception as e:
        return f"ERROR RAG historial: {str(e)}"


@tool
def integrar_datos(id_equipo: str) -> str:
    """Obtiene datos del equipo y repuestos desde los CSV locales.
    Args:
        id_equipo: ID del equipo (ej. EQA-1001)
    """
    if _df_equipos is None:
        return "ERROR: CSV no cargados."
    eid = id_equipo.strip().upper()
    feq = _df_equipos[_df_equipos["ID"] == eid]
    if feq.empty:
        ids = sorted(_df_equipos["ID"].tolist())
        return f"Equipo '{eid}' no encontrado. IDs disponibles: {ids}"
    eq       = feq.iloc[0]
    info_rep = "Sin datos de repuesto."
    if _df_repuestos is not None:
        frep = _df_repuestos[_df_repuestos["ID_Equipo"] == eid]
        if not frep.empty:
            rep      = frep.iloc[0]
            stock    = rep.get("Stock_Unidades",     rep.get("Stock", "N/A"))
            repuesto = rep.get("Repuesto_Principal", rep.get("Repuesto", "N/A"))
            tiempo   = rep.get("Tiempo_Reposicion",  rep.get("TiempoReposicion", "N/A"))
            estado   = rep.get("Estado_Stock", "N/A")
            info_rep = (
                f"Repuesto: {repuesto} | Stock: {stock} unidades | "
                f"Estado: {estado} | Tiempo reposicion: {tiempo}"
            )
    return (
        f"ID: {eid} | Nombre: {eq.get('Nombre','N/A')} | "
        f"Tipo: {eq.get('Tipo','N/A')} | "
        f"Ubicacion: {eq.get('Ubicacion','N/A')} | "
        f"Criticidad: {eq.get('Criticidad','N/A')} | "
        f"Norma: {eq.get('Norma_Aplicable','N/A')} | "
        f"{info_rep}"
    )


@tool
def generar_orden_trabajo(
    id_equipo:         str,
    reporte:           str,
    criticidad:        str,
    ubicacion:         str,
    nota_preventiva:   str,
    historial_texto:   str,
    stock_repuesto:    str,
    tiempo_reposicion: str,
    responsable:       str = "Tecnico de turno",
) -> str:
    """Genera la Orden de Trabajo en PDF con el analisis completo.
    Args:
        id_equipo, reporte (SOLO la falla original), criticidad,
        ubicacion, nota_preventiva, historial_texto,
        stock_repuesto, tiempo_reposicion, responsable
    """
    global _orden_contador
    ACCIONES = {
        "Alta":  "[URGENTE] DETENCION INMEDIATA. Notificar supervision.",
        "Media": "[ALERTA] Intervenir en max 48h.",
        "Baja":  "[INFO] Programar en proxima ventana.",
    }
    accion = ACCIONES.get(criticidad.strip().capitalize(), "Consultar con supervisor.")
    _orden_contador += 1
    orden_num  = _orden_contador
    os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)
    nombre_pdf = f"{PDF_OUTPUT_DIR}/Orden_N{orden_num:03d}_{id_equipo}.pdf"

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", style="B", size=13)
        pdf.set_fill_color(30, 80, 160)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 12,
            f"ORDEN DE TRABAJO N{chr(176)}{orden_num} | Prioridad: {criticidad.upper()}",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C", fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", size=9)
        pdf.ln(2)
        pdf.cell(0, 6,
            f"Empresa: Hidrocarburos del Peru | "
            f"Emitida: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')} | "
            f"Equipo: {id_equipo}",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)
        pdf.set_fill_color(225, 235, 255)
        secciones = [
            ("1. Falla reportada",          reporte),
            ("2. ID del equipo",             id_equipo),
            ("3. Ubicacion",                 ubicacion),
            ("4. Criticidad",                criticidad),
            ("5. Accion recomendada",        accion),
            ("6. Nota preventiva",           nota_preventiva),
            ("7. Historial de fallas",       historial_texto),
            ("8. Stock repuesto",
             f"Stock: {stock_repuesto} | Reposicion: {tiempo_reposicion}"),
            ("9. Responsable",               responsable),
        ]
        for titulo, contenido in secciones:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 7, titulo,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
            pdf.set_font("Helvetica", size=9)
            pdf.multi_cell(0, 5, (contenido or "Sin informacion.").strip())
            pdf.ln(1)
        pdf.output(nombre_pdf)
        kb = os.path.getsize(nombre_pdf) / 1024
        log.info(f"PDF generado: {nombre_pdf} ({kb:.1f} KB)")
        return (
            f"Orden N{chr(176)}{orden_num} generada: {nombre_pdf} | "
            f"Equipo: {id_equipo} | Criticidad: {criticidad} | {kb:.1f} KB"
        )
    except Exception as e:
        return f"ERROR generando PDF: {str(e)}"


# ── Inicialización del agente ─────────────────────────────────────
def inicializar_agente():
    """Inicializa el agente una sola vez al arrancar el backend."""
    global _agente
    log.info("Inicializando agente LangChain...")
    _init_vector_store()
    _init_csv()
    os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

    modelo  = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
    memoria = MemorySaver()
    todas   = [consultar_normativas, consultar_historial,
               integrar_datos, generar_orden_trabajo]

    _agente = create_react_agent(
        model=modelo,
        tools=todas,
        checkpointer=memoria,
        prompt=SYSTEM_PROMPT,
    )
    log.info(f"Agente listo con {len(todas)} tools")
    return _agente


def get_agente():
    """Devuelve el agente inicializado."""
    if _agente is None:
        raise RuntimeError("Agente no inicializado. Llamar inicializar_agente() primero.")
    return _agente


def get_vector_store():
    """Devuelve el vector store para el health check."""
    return _vector_store
