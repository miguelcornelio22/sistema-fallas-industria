#!/bin/bash
# ================================================================
# deploy_backend.sh — Despliegue del backend FastAPI en Cloud Run
# Uso: bash deploy_backend.sh
# ================================================================
set -euo pipefail

PROJECT_ID="cobalto-data2"
REGION="us-west4"
REPO="mcp-repo"
SERVICE="backend-fallas"
IMAGE_TAG="v1"
ES_URL="http://34.125.122.137:9200"
INDEX_NAME="rag_fallas_pf_v1"

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}:${IMAGE_TAG}"

echo "================================================================"
echo "Desplegando Backend FastAPI — Proyecto Final"
echo "  Imagen  : ${IMAGE}"
echo "  ES URL  : ${ES_URL}"
echo "================================================================"

gcloud config set project "${PROJECT_ID}"

# Build de la imagen
echo "[1/2] Construyendo imagen Docker..."
gcloud builds submit \
    --tag "${IMAGE}" \
    --timeout=600s \
    .
echo "OK — Imagen: ${IMAGE}"

# Deploy en Cloud Run
echo "[2/2] Desplegando en Cloud Run..."
gcloud run deploy "${SERVICE}" \
    --image "${IMAGE}" \
    --region "${REGION}" \
    --platform managed \
    --port 8000 \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 1 \
    --max-instances 3 \
    --timeout 300 \
    --set-secrets "OPENAI_API_KEY=openai-api-key:latest" \
    --set-secrets "ES_PASSWORD=es-password:latest" \
    --set-env-vars "ES_URL=${ES_URL}" \
    --set-env-vars "INDEX_NAME=${INDEX_NAME}" \
    --set-env-vars "PDF_OUTPUT_DIR=/tmp/ordenes_generadas" \
    --allow-unauthenticated \
    --quiet

SERVICE_URL=$(gcloud run services describe "${SERVICE}" \
    --region="${REGION}" \
    --format="value(status.url)")

echo ""
echo "================================================================"
echo "DESPLIEGUE COMPLETADO"
echo "================================================================"
echo "URL del backend : ${SERVICE_URL}"
echo "POST /consulta  : ${SERVICE_URL}/consulta"
echo "GET  /health    : ${SERVICE_URL}/health"
echo "GET  /docs      : ${SERVICE_URL}/docs"
echo ""
echo "Guardar en Drive/credenciales/backend_url.txt:"
echo "${SERVICE_URL}"
echo "================================================================"
