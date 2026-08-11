# ================================================================
# app.py — Frontend Streamlit
# Sistema de Gestión de Fallas — Hidrocarburos del Perú
# Proyecto Final IA Generativa
# ================================================================
 
import streamlit as st
import requests
import os
import uuid
from datetime import datetime
 
BACKEND_URL = os.environ.get(
    "BACKEND_URL",
    "https://backend-fallas-26134329034.us-central1.run.app"
).rstrip("/")
 
st.set_page_config(
    page_title="Gestión de Fallas — Hidrocarburos del Perú",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
st.markdown("""
<style>
.main-header{background:linear-gradient(135deg,#0d1b2a 0%,#1b2d42 100%);
padding:1.2rem 1.8rem;border-radius:10px;margin-bottom:1.5rem;
border-left:4px solid #2563eb}
.main-title{font-size:20px;font-weight:600;color:#e2e8f0;margin:0}
.main-sub{font-size:13px;color:#94a3b8;margin:4px 0 0 0}
.msg-user{background:#1e3a5f;border-radius:10px 10px 2px 10px;
padding:10px 14px;margin:8px 0;color:#e2e8f0;font-size:14px;
border-left:3px solid #2563eb}
.msg-agent{background:#1a2332;border-radius:10px 10px 10px 2px;
padding:10px 14px;margin:8px 0;color:#cbd5e1;font-size:13px;
border-left:3px solid #16a34a;line-height:1.6}
.rag-source{background:#0f172a;border:1px solid #1e3a5f;border-radius:6px;
padding:6px 10px;margin:4px 0;font-size:11px;color:#64748b;font-family:monospace}
.rag-title{font-size:11px;font-weight:500;color:#475569;text-transform:uppercase;
letter-spacing:0.05em;margin:8px 0 4px 0}
.tool-badge{display:inline-block;background:#1e3a5f;color:#60a5fa;
font-size:11px;padding:2px 8px;border-radius:20px;margin:2px;font-family:monospace}
.sidebar-section{background:#0f172a;border-radius:8px;padding:10px 12px;
margin-bottom:10px;border:1px solid #1e293b}
.warn-box{background:#422006;border:1px solid #854d0e;border-radius:6px;
padding:8px 12px;font-size:12px;color:#fbbf24;margin-top:6px}
</style>
""", unsafe_allow_html=True)
 
# Session state
for key, val in {
    "session_id": str(uuid.uuid4()),
    "mensajes":   [],
    "backend_ok": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val
 
 
def verificar_backend() -> bool:
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=10)
        return r.json().get("status") == "ok"
    except Exception:
        return False
 
 
def llamar_backend(mensaje: str) -> dict:
    payload = {
        "session_id": st.session_state.session_id,
        "mensaje":    mensaje,
    }
    r = requests.post(
        f"{BACKEND_URL}/consulta",
        json=payload,
        timeout=120,
    )
    r.raise_for_status()
    return r.json()
 
 
def nueva_sesion():
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.mensajes   = []
 
 
# Header
st.markdown("""
<div class="main-header">
    <p class="main-title">🔧 Sistema de Gestión de Fallas</p>
    <p class="main-sub">Hidrocarburos del Perú · IA Generativa · Proyecto Final</p>
</div>
""", unsafe_allow_html=True)
 
# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Panel de control")
 
    if st.button("🔄 Verificar sistema", use_container_width=True):
        st.session_state.backend_ok = verificar_backend()
 
    if st.session_state.backend_ok is True:
        st.success("Sistema operativo")
    elif st.session_state.backend_ok is False:
        st.error("Backend no disponible")
    else:
        st.info("Presiona Verificar sistema")
 
    st.divider()
    st.markdown("### 💬 Sesión activa")
    st.markdown(f"""
    <div class="sidebar-section">
        <div style="font-size:11px;color:#64748b">Session ID</div>
        <div style="font-size:11px;color:#94a3b8;font-family:monospace;word-break:break-all">
            {st.session_state.session_id[:20]}...
        </div>
        <div style="font-size:11px;color:#64748b;margin-top:6px">Mensajes</div>
        <div style="font-size:13px;color:#e2e8f0">{len(st.session_state.mensajes)}</div>
    </div>
    """, unsafe_allow_html=True)
 
    if st.button("🗑️ Nueva sesión", use_container_width=True):
        nueva_sesion()
        st.rerun()
 
    st.divider()
    st.markdown("### 📋 Guía de uso")
    st.markdown("""
    **Reportar una falla:**
    ```
    Bomba EQA-1001 Planta Cusco,
    presión baja, ruido anormal
    ```
    **Consulta normativa:**
    ```
    Que dice el DS 081 sobre
    inspección de compresores?
    ```
    **Consulta de equipo:**
    ```
    Datos del equipo EQA-1003
    ```
    """)
 
    st.divider()
    st.markdown(
        '<div style="font-size:11px;color:#475569;text-align:center">'
        'Powered by LangChain · GPT-4o · RAG<br>'
        'Proyecto Final IA Generativa 2026'
        '</div>',
        unsafe_allow_html=True
    )
 
# Layout principal
col_chat, col_info = st.columns([2, 1], gap="large")
 
with col_chat:
    st.subheader("💬 Consulta al agente")
 
    # Historial de mensajes
    for msg in st.session_state.mensajes:
        if msg["rol"] == "usuario":
            st.markdown(
                f'<div class="msg-user">👤 {msg["contenido"]}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="msg-agent">🤖 {msg["contenido"]}</div>',
                unsafe_allow_html=True
            )
 
            # Fuentes RAG
            if msg.get("fuentes_rag"):
                st.markdown(
                    '<div class="rag-title">📄 Fuentes RAG consultadas</div>',
                    unsafe_allow_html=True
                )
                for f in msg["fuentes_rag"]:
                    st.markdown(
                        f'<div class="rag-source">'
                        f'📑 {f["source"]} · Pág. {f["page"]} · Score {f["score"]:.3f}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
 
            # Tools usadas
            if msg.get("tools_usadas"):
                tools_html = "".join([
                    f'<span class="tool-badge">⚙️ {t}</span>'
                    for t in msg["tools_usadas"]
                ])
                st.markdown(
                    f'<div style="margin-top:6px">{tools_html}</div>',
                    unsafe_allow_html=True
                )
 
            # PDF — botón de descarga directa
            if msg.get("orden_pdf") and msg.get("orden_pdf_url"):
                nombre_pdf = msg["orden_pdf"]
                pdf_url    = f"{BACKEND_URL}{msg['orden_pdf_url']}"
                st.markdown(f"""
                <div style="margin-top:10px">
                    <a href="{pdf_url}" target="_blank"
                       style="background:#14532d;color:#4ade80;
                              padding:7px 14px;border-radius:6px;
                              font-size:12px;text-decoration:none;
                              font-family:monospace;font-weight:500">
                        📥 Descargar {nombre_pdf}
                    </a>
                </div>
                """, unsafe_allow_html=True)
 
                # Aviso sobre la naturaleza temporal de Cloud Run
                st.markdown("""
                <div class="warn-box">
                    ⚠️ <strong>Nota:</strong> El PDF está disponible mientras
                    la misma instancia del servidor esté activa.
                    Si el enlace no funciona, genera una nueva consulta.
                </div>
                """, unsafe_allow_html=True)
 
    # Formulario de entrada
    st.markdown("---")
    with st.form("form_consulta", clear_on_submit=True):
        mensaje = st.text_area(
            "Describe la falla o escribe tu consulta:",
            placeholder=(
                "Ej: Bomba EQA-1001 Planta Cusco presenta presión baja "
                "y vibración excesiva. ¿Qué acción debo tomar?"
            ),
            height=100,
            label_visibility="collapsed",
        )
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            enviar = st.form_submit_button(
                "📤 Enviar consulta",
                type="primary",
                use_container_width=True,
            )
        with col_btn2:
            st.form_submit_button(
                "🗑️ Limpiar",
                use_container_width=True,
                on_click=nueva_sesion,
            )
 
    # Procesar consulta
    if enviar and mensaje.strip():
        st.session_state.mensajes.append({
            "rol":       "usuario",
            "contenido": mensaje.strip(),
            "timestamp": datetime.now().isoformat(),
        })
 
        with st.spinner("🤖 El agente está analizando la falla..."):
            try:
                data = llamar_backend(mensaje.strip())
                st.session_state.mensajes.append({
                    "rol":          "agente",
                    "contenido":    data.get("respuesta", "Sin respuesta."),
                    "fuentes_rag":  data.get("fuentes_rag", []),
                    "tools_usadas": data.get("tools_usadas", []),
                    "orden_pdf":    data.get("orden_pdf"),
                    "orden_pdf_url": data.get("orden_pdf_url"),
                    "timestamp":    datetime.now().isoformat(),
                })
                st.rerun()
            except requests.exceptions.Timeout:
                st.error("⏱ El agente tardó más de 120 segundos. Intenta con una consulta más simple.")
            except requests.exceptions.ConnectionError:
                st.error("❌ No se puede conectar al backend. Verifica que el servicio esté activo.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
 
# Panel de información
with col_info:
    st.subheader("📊 Información del sistema")
 
    with st.expander("🔩 Equipos disponibles", expanded=True):
        equipos = [
            ("EQA-1001", "Bomba Principal",     "Cusco",    "Alta"),
            ("EQA-1002", "Válvula de Control",  "Cusco",    "Media"),
            ("EQA-1003", "Compresor A",          "Cusco",    "Alta"),
            ("EQA-1004", "Generador Diesel",     "Cusco",    "Alta"),
            ("EQA-2001", "Bomba Secundaria",     "Lima",     "Alta"),
            ("EQA-2003", "Compresor B",          "Lima",     "Alta"),
            ("EQA-3003", "Compresor C",          "Arequipa", "Alta"),
            ("EQA-4001", "Bomba Transferencia",  "Piura",    "Alta"),
            ("EQA-4003", "Compresor D",          "Piura",    "Alta"),
        ]
        for eid, nombre, planta, crit in equipos:
            color = "#ef4444" if crit == "Alta" else "#f59e0b"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:4px 0;border-bottom:1px solid #1e293b;font-size:12px">'
                f'<span style="color:#94a3b8;font-family:monospace">{eid}</span>'
                f'<span style="color:#cbd5e1">{nombre}</span>'
                f'<span style="color:{color};font-size:10px">{crit}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
 
    with st.expander("📚 Normativas en el RAG"):
        normativas = [
            ("DS 081-2007-EM", "Reglamento de Transporte de Gas"),
            ("DS 018-2004-EM", "Norma de Servicio de Transporte"),
            ("ASME B31.4",     "Tuberías de Líquidos"),
            ("ASME B31.8",     "Sistemas de Gasoductos"),
            ("Historial SAP",  "Fallas Mantenimiento TGP"),
        ]
        for codigo, desc in normativas:
            st.markdown(
                f'<div style="padding:4px 0;border-bottom:1px solid #1e293b">'
                f'<div style="font-size:11px;color:#60a5fa;font-family:monospace">{codigo}</div>'
                f'<div style="font-size:11px;color:#64748b">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
 
    with st.expander("📈 Métricas"):
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Chunks RAG", "2,665")
        col_m2.metric("Equipos",    "16")
        col_m1.metric("Normativas", "5 docs")
        col_m2.metric("Tools",      "4")
 