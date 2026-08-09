#!/bin/bash
# ================================================================
# deploy_mcp.sh — Despliegue del MCP Server en Cloud Run
# Proyecto Final — Hidrocarburos del Perú
# Uso: bash deploy_mcp.sh
# ================================================================

set -euo pipefail

# ── CONFIGURACIÓN — verificar estos valores antes de ejecutar ─────
PROJECT_ID="cobalto-data2"
REGION="us-west4"
REPO="mcp-repo"
SERVICE="mcp-mantenimiento"
IMAGE_TAG="v2"

# Elasticsearch — nueva IP del proyecto final
ES_URL="http://34.50.186.40:9200"
ES_USER="elastic"
INDEX_NAME="rag_fallas_pf_v1"

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}:${IMAGE_TAG}"

echo "================================================================"
echo "Desplegando MCP Server — Proyecto Final"
echo "  Proyecto  : ${PROJECT_ID}"
echo "  Imagen    : ${IMAGE}"
echo "  ES URL    : ${ES_URL}"
echo "  Index     : ${INDEX_NAME}"
echo "================================================================"

# ── Paso 1: Configurar proyecto ───────────────────────────────────
gcloud config set project "${PROJECT_ID}"

# ── Paso 2: Habilitar APIs ────────────────────────────────────────
echo "[1/5] Habilitando APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    --quiet
echo "OK"

# ── Paso 3: Crear repositorio Artifact Registry si no existe ──────
echo "[2/5] Verificando Artifact Registry..."
if ! gcloud artifacts repositories describe "${REPO}" \
        --location="${REGION}" --quiet 2>/dev/null; then
    gcloud artifacts repositories create "${REPO}" \
        --repository-format=docker \
        --location="${REGION}" \
        --description="Repositorio MCP Hidrocarburos del Peru"
    echo "Repositorio creado."
else
    echo "Repositorio ya existe."
fi

# ── Paso 4: Actualizar secretos en Secret Manager ─────────────────
echo "[3/5] Actualizando secretos..."

# OpenAI API Key
if ! gcloud secrets describe openai-api-key --quiet 2>/dev/null; then
    echo "Ingresa tu OpenAI API Key (sk-...):"
    read -rs OPENAI_KEY
    echo -n "${OPENAI_KEY}" | gcloud secrets create openai-api-key \
        --data-file=- --replication-policy=automatic
    echo "Secreto openai-api-key creado."
else
    echo "openai-api-key ya existe. Para actualizar:"
    echo "  echo -n 'NUEVA_KEY' | gcloud secrets versions add openai-api-key --data-file=-"
fi

# ES Password
if ! gcloud secrets describe es-password --quiet 2>/dev/null; then
    echo "Ingresa el password de Elasticsearch:"
    read -rs ES_PASS
    echo -n "${ES_PASS}" | gcloud secrets create es-password \
        --data-file=- --replication-policy=automatic
    echo "Secreto es-password creado."
else
    echo "Actualizando es-password con nueva version..."
    echo "Ingresa el password de Elasticsearch:"
    read -rs ES_PASS
    echo -n "${ES_PASS}" | gcloud secrets versions add es-password \
        --data-file=-
    echo "es-password actualizado."
fi

# ── Paso 5: Build de la imagen ────────────────────────────────────
echo "[4/5] Construyendo imagen Docker..."
gcloud builds submit \
    --tag "${IMAGE}" \
    --timeout=600s \
    .
echo "OK — Imagen: ${IMAGE}"

# ── Paso 6: Deploy en Cloud Run ───────────────────────────────────
echo "[5/5] Desplegando en Cloud Run..."
gcloud run deploy "${SERVICE}" \
    --image "${IMAGE}" \
    --region "${REGION}" \
    --platform managed \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 1 \
    --max-instances 5 \
    --timeout 300 \
    --set-secrets "OPENAI_API_KEY=openai-api-key:latest" \
    --set-secrets "ES_PASSWORD=es-password:latest" \
    --set-env-vars "ES_URL=${ES_URL}" \
    --set-env-vars "ES_USER=${ES_USER}" \
    --set-env-vars "INDEX_NAME=${INDEX_NAME}" \
    --set-env-vars "PDF_OUTPUT_DIR=/tmp/ordenes_generadas" \
    --set-env-vars "RAG_TOP_K=5" \
    --set-env-vars "RAG_SCORE_MIN=0.70" \
    --no-allow-unauthenticated \
    --quiet

# ── Resultado ─────────────────────────────────────────────────────
SERVICE_URL=$(gcloud run services describe "${SERVICE}" \
    --region="${REGION}" \
    --format="value(status.url)")

echo ""
echo "================================================================"
echo "DESPLIEGUE COMPLETADO"
echo "================================================================"
echo "URL del servicio : ${SERVICE_URL}"
echo "Endpoint SSE MCP : ${SERVICE_URL}/sse"
echo "Health check     : ${SERVICE_URL}/health"
echo ""
echo "Guardar en Drive/credenciales/mcp_url.txt:"
echo "${SERVICE_URL}/sse"
echo "================================================================"
