# ================================================================
# SERVIDOR MCP — mantenimiento_fallas_server
# Proyecto Final — Hidrocarburos del Perú
# Versión compatible con fastmcp==2.14.7 en Cloud Run
# ================================================================

import os
import uuid
import datetime
import logging
import threading

import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("mcp-mantenimiento")

# ── Configuración ─────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ES_URL         = os.environ.get("ES_URL",      "http://34.50.186.40:9200")
ES_USER        = os.environ.get("ES_USER",     "elastic")
ES_PASSWORD    = os.environ.get("ES_PASSWORD", "")
INDEX_NAME     = os.environ.get("INDEX_NAME",  "rag_fallas_pf_v1")
EMBED_MODEL    = "text-embedding-3-large"
RAG_TOP_K      = int(os.environ.get("RAG_TOP_K",      "5"))
RAG_SCORE_MIN  = float(os.environ.get("RAG_SCORE_MIN", "0.70"))

CSV_EQUIPOS    = os.environ.get("CSV_EQUIPOS",   "/app/data/equipos.csv")
CSV_REPUESTOS  = os.environ.get("CSV_REPUESTOS", "/app/data/repuestos.csv")
PDF_OUTPUT_DIR = os.environ.get("PDF_OUTPUT_DIR", "/tmp/ordenes_generadas")
PORT           = int(os.environ.get("PORT", "8080"))

FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ── Estado global ─────────────────────────────────────────────────
equipos      = None
repuestos    = None
IDS_VALIDOS  = set()
vector_store = None

# ── Crear servidor MCP — API correcta para fastmcp 2.14.7 ────────
mcp = FastMCP("mantenimiento_fallas_server")


# ── Inicialización (se llama en thread separado al arrancar) ──────
def _inicializar():
    global equipos, repuestos, IDS_VALIDOS, vector_store

    log.info("=== Iniciando inicialización en background ===")
    os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

    if not OPENAI_API_KEY:
        log.warning("OPENAI_API_KEY no configurada")
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

    # Cargar CSV
    try:
        equipos   = pd.read_csv(CSV_EQUIPOS,   encoding="latin1", sep=";")
        repuestos = pd.read_csv(CSV_REPUESTOS, encoding="latin1", sep=";")
        IDS_VALIDOS.update(equipos["ID"].astype(str).str.strip())
        log.info(f"CSV: {len(equipos)} equipos, {len(repuestos)} repuestos")
        log.info(f"IDs: {sorted(IDS_VALIDOS)}")
    except Exception as e:
        log.error(f"Error CSV: {e}")

    # Conectar Elasticsearch
    try:
        from langchain_openai import OpenAIEmbeddings
        from langchain_elasticsearch import ElasticsearchStore

        embeddings = OpenAIEmbeddings(model=EMBED_MODEL)
        vector_store = ElasticsearchStore(
            index_name=INDEX_NAME,
            embedding=embeddings,
            es_url=ES_URL,
            es_user=ES_USER,
            es_password=ES_PASSWORD,
        )
        log.info(f"Elasticsearch OK: {ES_URL} / {INDEX_NAME}")
    except Exception as e:
        log.error(f"Error Elasticsearch: {e}")

    log.info("=== Inicialización completada ===")


# ================================================================
# TOOL 1 — consultar_historial
# ================================================================
@mcp.tool()
def consultar_historial(query: str) -> str:
    """
    Busca fallas similares en el historial SAP usando RAG semántico.
    Args:
        query: descripción de la falla en texto libre.
    """
    if vector_store is None:
        return "Elasticsearch no disponible aún. Reintentar en 30 segundos."
    try:
        resultados = vector_store.similarity_search_with_score(query, k=RAG_TOP_K)
        filtrados  = [(d, s) for d, s in resultados if s >= RAG_SCORE_MIN]

        if not filtrados:
            return (
                f"Sin registros con similitud >= {RAG_SCORE_MIN}. "
                "Falla posiblemente sin precedentes en el historial SAP."
            )
        partes = []
        for i, (doc, score) in enumerate(filtrados, 1):
            m = doc.metadata
            partes.append(
                f"[Registro {i} | Score: {score:.3f}] "
                f"Fuente: {m.get('doc_name','?')} | "
                f"Pag: {m.get('page','?')} | "
                f"Equipos: {m.get('equipos_ref','N/A')} | "
                f"Extracto: {doc.page_content[:350]}..."
            )
        return "\n\n".join(partes)
    except Exception as e:
        return f"ERROR al consultar historial: {str(e)}"


# ================================================================
# TOOL 2 — integrar_datos
# ================================================================
@mcp.tool()
def integrar_datos(id_equipo: str) -> str:
    """
    Devuelve datos del equipo y repuestos desde los CSV locales.
    Args:
        id_equipo: ID del equipo (ej. EQA-1001)
    """
    if equipos is None:
        return "CSV no cargados aún. Reintentar en 30 segundos."

    eid = id_equipo.strip().upper()
    feq = equipos[equipos["ID"] == eid]

    if feq.empty:
        return (
            f"Equipo '{eid}' no encontrado. "
            f"IDs disponibles: {sorted(IDS_VALIDOS)}"
        )

    eq = feq.iloc[0]

    info_rep = "Sin datos de repuesto."
    if repuestos is not None:
        frep = repuestos[repuestos["ID_Equipo"] == eid]
        if not frep.empty:
            rep = frep.iloc[0]
            stock    = rep.get("Stock_Unidades", rep.get("Stock", "N/A"))
            repuesto = rep.get("Repuesto_Principal", rep.get("Repuesto", "N/A"))
            tiempo   = rep.get("Tiempo_Reposicion", rep.get("TiempoReposicion", "N/A"))
            estado   = rep.get("Estado_Stock", "N/A")
            info_rep = (
                f"Repuesto: {repuesto} | "
                f"Stock: {stock} unidades | "
                f"Estado: {estado} | "
                f"Tiempo reposicion: {tiempo}"
            )

    return (
        f"ID: {eid} | "
        f"Nombre: {eq.get('Nombre','N/A')} | "
        f"Tipo: {eq.get('Tipo','N/A')} | "
        f"Ubicacion: {eq.get('Ubicacion','N/A')} | "
        f"Criticidad: {eq.get('Criticidad','N/A')} | "
        f"Norma: {eq.get('Norma_Aplicable','N/A')} | "
        f"{info_rep}"
    )


# ================================================================
# TOOL 3 — generar_orden_trabajo
# ================================================================
@mcp.tool()
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
    """
    Genera la Orden de Trabajo en PDF con 9 secciones.
    Args:
        id_equipo, reporte, criticidad, ubicacion,
        nota_preventiva, historial_texto,
        stock_repuesto, tiempo_reposicion,
        responsable (default: Tecnico de turno)
    """
    ACCIONES = {
        "Alta":  "[URGENTE] DETENCION INMEDIATA. Notificar supervision.",
        "Media": "[ALERTA] Intervenir en max 48h. Monitorear parametros.",
        "Baja":  "[INFO] Programar en proxima ventana de mantenimiento.",
    }
    accion = ACCIONES.get(
        criticidad.strip().capitalize(),
        "Consultar con supervisor."
    )

    alerta_stock = ""
    try:
        sn = int(str(stock_repuesto).strip())
        if sn == 0:
            alerta_stock = f"[CRITICO] Sin stock. Reposicion: {tiempo_reposicion}."
        elif sn <= 2:
            alerta_stock = f"[ALERTA] Stock bajo ({sn} unid.)."
    except ValueError:
        alerta_stock = f"Stock: {stock_repuesto}"

    orden_id   = uuid.uuid4().hex[:8].upper()
    nombre_pdf = os.path.join(PDF_OUTPUT_DIR, f"Orden_{id_equipo}_{orden_id}.pdf")

    def _limpiar(texto: str) -> str:
        for k, v in {
            "\u26d4":"[URGENTE]", "\u26a0\ufe0f":"[ALERTA]",
            "\u2139\ufe0f":"[INFO]", "\U0001f6a8":"[CRITICO]",
            "\u2714":"[OK]", "\u2014":"-", "\u2013":"-",
        }.items():
            texto = texto.replace(k, v)
        return texto

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("DejaVu",            fname=FONT_REGULAR)
        pdf.add_font("DejaVu", style="B", fname=FONT_BOLD)

        pdf.set_font("DejaVu", style="B", size=13)
        pdf.set_fill_color(30, 80, 160)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 12,
            f"ORDEN DE TRABAJO {orden_id} | Prioridad: {criticidad.upper()}",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C", fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("DejaVu", size=9)
        pdf.ln(2)
        pdf.cell(0, 6,
            f"Empresa: Hidrocarburos del Peru | "
            f"Emitida: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)

        stock_txt = f"Stock: {stock_repuesto} unid. | Reposicion: {tiempo_reposicion}"
        if alerta_stock:
            stock_txt += f"\n{alerta_stock}"

        pdf.set_fill_color(225, 235, 255)
        secciones = [
            ("1. Falla reportada",           _limpiar(reporte)),
            ("2. ID del equipo",              id_equipo),
            ("3. Ubicacion",                  _limpiar(ubicacion)),
            ("4. Criticidad",                 criticidad),
            ("5. Accion recomendada",         accion),
            ("6. Nota preventiva (RAG/SAP)",  _limpiar(nota_preventiva)),
            ("7. Historial de fallas",        _limpiar(historial_texto)),
            ("8. Repuestos y stock",          _limpiar(stock_txt)),
            ("9. Responsable asignado",       _limpiar(responsable)),
        ]
        for titulo, contenido in secciones:
            pdf.set_font("DejaVu", "B", 10)
            pdf.cell(0, 7, titulo,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
            pdf.set_font("DejaVu", size=9)
            pdf.multi_cell(0, 5, (contenido or "Sin informacion.").strip())
            pdf.ln(1)

        pdf.output(nombre_pdf)

        if not os.path.exists(nombre_pdf):
            return f"ERROR: PDF no creado en {nombre_pdf}"

        kb = os.path.getsize(nombre_pdf) / 1024
        log.info(f"PDF generado: {nombre_pdf} ({kb:.1f} KB)")
        return (
            f"Orden generada: {nombre_pdf} | "
            f"ID: {orden_id} | Equipo: {id_equipo} | "
            f"Criticidad: {criticidad} | {kb:.1f} KB"
        )

    except Exception as e:
        import traceback
        return f"ERROR PDF: {str(e)}\n{traceback.format_exc()}"


# ================================================================
# RESOURCE — listar órdenes
# ================================================================
@mcp.resource("ordenes://lista")
def listar_ordenes() -> str:
    """Lista todas las órdenes PDF generadas en el servidor."""
    import glob
    pdfs = sorted(glob.glob(os.path.join(PDF_OUTPUT_DIR, "Orden_*.pdf")))
    if not pdfs:
        return "Sin ordenes generadas todavia."
    lineas = [f"Total: {len(pdfs)} ordenes"]
    for p in pdfs:
        kb = os.path.getsize(p) / 1024
        lineas.append(f"  {os.path.basename(p)} ({kb:.1f} KB)")
    return "\n".join(lineas)


# ================================================================
# PUNTO DE ENTRADA
# ================================================================
if __name__ == "__main__":
    log.info(f"Arrancando servidor MCP en puerto {PORT}")

    # Lanzar inicialización en thread separado
    # El servidor HTTP levanta primero y Cloud Run pasa el health check
    # La inicialización de ES y CSV ocurre en background
    t = threading.Thread(target=_inicializar, daemon=True)
    t.start()

    # Arrancar el servidor MCP con transporte SSE
    # fastmcp 2.14.7 expone /health automáticamente
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=PORT,
    )
