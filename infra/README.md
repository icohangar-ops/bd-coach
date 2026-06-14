# BD Coach — infra/

(Formerly the `bd-coach-infra` repo; now the infra half of the unified `bd-coach` repo.)

Docker Compose stack and CI for BD Coach. Deploys to **any Linux host** with Docker — no cloud vendor lock-in.

## Stack

| Service | Image | Purpose |
|---|---|---|
| `librechat` | `ghcr.io/danny-avila/librechat` | Agent UI + OIDC + tool dispatch |
| `litellm` | `ghcr.io/berriai/litellm` | Model gateway + DLP/audit hooks |
| `ollama` | `ollama/ollama` | Local LLM inference |
| `rasa` | `rasa/rasa:3.6.20-full` | Topic/intent classifier |
| `n8n` | `docker.n8n.io/n8nio/n8n` | Flow engine (8 flows) |
| `mattermost` | `mattermost/mattermost-team-edition` | Chat channel + DMs |
| `keycloak` | `quay.io/keycloak/keycloak` | OIDC identity |
| `baserow` | `baserow/baserow` | Pipeline + dashboard tables |
| `nextcloud` | `nextcloud:29-apache` | Documents + CalDAV |
| `minio` | `minio/minio` | Audit archive (S3) |
| `whisper` | `fedirz/faster-whisper-server` | Transcript ingestion |
| `qdrant` | `qdrant/qdrant` | Vector DB (RAG) |
| `postgres` | `postgres:16` | Shared relational store |
| `vault` | `hashicorp/vault` | Secrets (dev mode) |
| `openobserve` | `openobserve` | Logs |
| `grafana` + `prometheus` | — | Dashboards + metrics |
| `traefik` | `traefik:v3.1` | TLS reverse proxy |

## First boot

```bash
cp .env.example .env
# Set BD_COACH_DOMAIN, passwords, BASEROW_* table IDs
docker compose -f compose/docker-compose.yml up -d
chmod +x scripts/bootstrap.sh && ./scripts/bootstrap.sh
```

### Hostinger VPS

See **[docs/HOSTINGER.md](docs/HOSTINGER.md)** for full steps. Quick version:

```bash
sudo ./scripts/install-hostinger.sh   # once, as root
cp .env.example .env && nano .env     # set domain + secrets + GROQ_API_KEY
docker compose -f compose/docker-compose.yml \
  -f compose/docker-compose.hostinger.yml up -d
./scripts/bootstrap.sh
```

## DNS records

Point these A records to your host IP:

- `chat.${BD_COACH_DOMAIN}` — Mattermost
- `bd-coach.${BD_COACH_DOMAIN}` — LibreChat
- `n8n.${BD_COACH_DOMAIN}` — n8n
- `auth.${BD_COACH_DOMAIN}` — Keycloak
- `files.${BD_COACH_DOMAIN}` — Nextcloud
- `data.${BD_COACH_DOMAIN}` — Baserow
- `api.${BD_COACH_DOMAIN}` — LiteLLM
- `minio.${BD_COACH_DOMAIN}` — MinIO

## DR (optional second host)

- Postgres logical replication primary → standby
- MinIO bucket replication or nightly `mc mirror` to off-site
- Qdrant snapshot to MinIO daily
- RTO ~30 min, RPO ~5 min

## CI

- **GitHub Actions:** compose validate, yamllint, DLP tests, Trivy scan, optional SSH deploy, Codeberg mirror
- **Woodpecker (Codeberg):** lint + scan only
