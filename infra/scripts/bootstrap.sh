#!/usr/bin/env bash
# First-boot setup for BD Coach OSS stack.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Copy .env.example to .env and fill in values first."
  exit 1
fi

# shellcheck disable=SC1091
source .env

COMPOSE_FILES="${COMPOSE_FILES:-compose/docker-compose.yml}"
if [[ -f compose/docker-compose.hostinger.yml ]]; then
  COMPOSE_FILES="${COMPOSE_FILES} -f compose/docker-compose.hostinger.yml"
fi
if [[ "${BD_COACH_SLIM:-}" == "1" ]]; then
  COMPOSE_FILES="${COMPOSE_FILES} -f compose/docker-compose.slim.yml"
fi
COMPOSE_CMD=(docker compose -f compose/docker-compose.yml)
[[ -f compose/docker-compose.hostinger.yml ]] && COMPOSE_CMD+=(-f compose/docker-compose.hostinger.yml)
[[ "${BD_COACH_SLIM:-}" == "1" ]] && COMPOSE_CMD+=(-f compose/docker-compose.slim.yml)

CEO_MODEL="${OLLAMA_CEO_MODEL:-llama3.2:3b}"
BD_MODEL="${OLLAMA_BD_MODEL:-mistral:7b}"

echo "==> Pulling Ollama models (${CEO_MODEL}, ${BD_MODEL})..."
"${COMPOSE_CMD[@]}" exec -T ollama ollama pull "${CEO_MODEL}" || true
"${COMPOSE_CMD[@]}" exec -T ollama ollama pull "${BD_MODEL}" || true

echo "==> Creating MinIO audit bucket..."
"${COMPOSE_CMD[@]}" exec -T minio \
  mc alias set local http://localhost:9000 bdcoach "${MINIO_ROOT_PASSWORD}" 2>/dev/null || true
"${COMPOSE_CMD[@]}" exec -T minio \
  mc mb local/bd-coach-audit --with-lock 2>/dev/null || true

echo "==> Nextcloud folder layout (run once after Nextcloud is ready)..."
echo "    Create /BD/2026/Americas, /BD/2026/EMEA, /BD/Contracts, /BD/Reference, /BD/Transcripts"
echo "    via Nextcloud UI at https://files.${BD_COACH_DOMAIN}"

echo "==> Baserow tables to create manually or via API:"
echo "    bd_pipeline, activity_log, weekly_reports, scorecard, commission"
echo "    Export table IDs into BASEROW_TABLE_PIPELINE and BASEROW_TABLE_ACTIVITY"

echo "==> Import n8n flows:"
echo "    Settings → Import from file → config/n8n-flows/flows/*.json"

echo "==> DLP rule tests..."
python3 ../config/dlp/run_tests.py

echo "Bootstrap complete. Visit https://bd-coach.${BD_COACH_DOMAIN}"
