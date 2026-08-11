#!/bin/bash
set -euo pipefail

PROJECT_ID="cobalto-data2"
REGION="us-central1"
REPO="mcp-repo"
SERVICE="frontend-fallas"
IMAGE_TAG="v1"
BACKEND_URL="https://backend-fallas-26134329034.us-central1.run.app"

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}:${IMAGE_TAG}"

echo "================================================================"
echo "Desplegando Frontend Streamlit — Proyecto Final"
echo "  Imagen   : ${IMAGE}"
echo "  Backend  : ${BACKEND_URL}"
echo "================================================================"

gcloud config set project "${PROJECT_ID}"

echo "[1/2] Construyendo imagen Docker..."
gcloud builds submit \
    --tag "${IMAGE}" \
    --timeout=300s \
    .
echo "OK"

echo "[2/2] Desplegando en Cloud Run..."
gcloud run deploy "${SERVICE}" \
    --image "${IMAGE}" \
    --region "${REGION}" \
    --platform managed \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 3 \
    --timeout 120 \
    --set-env-vars "BACKEND_URL=${BACKEND_URL}" \
    --allow-unauthenticated \
    --quiet

SERVICE_URL=$(gcloud run services describe "${SERVICE}" \
    --region="${REGION}" \
    --format="value(status.url)")

echo ""
echo "================================================================"
echo "FRONTEND DESPLEGADO"
echo "================================================================"
echo "URL del portal : ${SERVICE_URL}"
echo "================================================================"
