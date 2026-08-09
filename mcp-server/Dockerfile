# ================================================================
# Dockerfile — MCP Server Gestión de Fallas
# Proyecto Final — Hidrocarburos del Perú
# Target: Google Cloud Run
# ================================================================

# ── Etapa 1: builder ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# ── Etapa 2: runtime ─────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="Hidrocarburos del Peru — Proyecto Final"
LABEL description="MCP Server para gestión de fallas de mantenimiento"
LABEL version="2.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PYTHONPATH=/app \
    PDF_OUTPUT_DIR=/tmp/ordenes_generadas \
    CSV_EQUIPOS=/app/data/equipos.csv \
    CSV_REPUESTOS=/app/data/repuestos.csv

# Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fonts-dejavu-core \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias Python del builder
COPY --from=builder /install /usr/local

# Crear usuario no-root
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home --shell /bin/false appuser

WORKDIR /app

# Crear directorio para PDFs
RUN mkdir -p /tmp/ordenes_generadas && \
    chown -R appuser:appgroup /tmp/ordenes_generadas

# Copiar archivos de datos y servidor
COPY --chown=appuser:appgroup data/equipos.csv   /app/data/equipos.csv
COPY --chown=appuser:appgroup data/repuestos.csv /app/data/repuestos.csv
COPY --chown=appuser:appgroup mcp_server_mantenimiento.py /app/

USER appuser
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

CMD ["sh", "-c", "python /app/mcp_server_mantenimiento.py"]
