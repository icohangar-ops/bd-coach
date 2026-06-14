# BD Coach

Unified repository for **BD Coach**, a self-hostable AI sales-operations assistant.
This repo merges what used to be two separate repos (`bd-coach-config` and
`bd-coach-infra`) into one product with two halves:

| Path | Was | Contents |
|---|---|---|
| [`config/`](config/) | `bd-coach-config` | Prompts, personas, DLP rules, topic intents, adaptive-card templates (JSON/YAML), and the DLP test harness. Version-controlled agent **behaviour**. |
| [`infra/`](infra/) | `bd-coach-infra` | The self-hostable Docker Compose **stack** (LibreChat, LiteLLM, Ollama, Rasa, n8n, Mattermost, Keycloak, Baserow, Nextcloud, MinIO, Qdrant, Postgres, Vault, observability, Traefik), deploy scripts, and docs. |

The infra stack mounts the config tree read-only at runtime (e.g. LiteLLM reads
`config/dlp/`, Rasa reads `config/topics/`, LibreChat and n8n read `config/`),
so the two halves are designed to live together.

## Layout

```
bd-coach/
├── config/      Agent behaviour (prompts, personas, DLP, topics, cards, knowledge)
│   ├── prompts/     Master system prompt (locked)
│   ├── personas/    CEO / USA_BD / EU_BD scopes → Keycloak groups
│   ├── topics/      Rasa intents + LibreChat tool mapping
│   ├── dlp/         HR/compensation regex rules + run_tests.py
│   ├── cards/       Adaptive-card JSON templates
│   └── knowledge/   Connector manifest
└── infra/       Self-hostable stack
    ├── compose/     docker-compose.yml (+ gpu / slim / hostinger overlays)
    ├── litellm/     Model gateway config + DLP/audit hooks
    ├── librechat/   Agent UI config
    ├── keycloak/    OIDC realm export
    ├── postgres/    DB init
    ├── observability/  Prometheus config
    ├── docs/        HOSTINGER.md and friends
    └── scripts/     bootstrap.sh, install-hostinger.sh
```

## Quick start

The stack runs from `infra/` and reads behaviour from `config/`.

```bash
cd infra
cp .env.example .env          # set BD_COACH_DOMAIN, passwords, BASEROW_* ids, GROQ_API_KEY
docker compose -f compose/docker-compose.yml --env-file .env up -d
chmod +x scripts/bootstrap.sh && ./scripts/bootstrap.sh
```

`bootstrap.sh` pulls Ollama models, creates the MinIO audit bucket, prints
manual setup steps, and runs the config DLP tests (`config/dlp/run_tests.py`).

Validate the behaviour half on its own at any time:

```bash
python config/dlp/run_tests.py
```

### Hostinger VPS

See **[infra/docs/HOSTINGER.md](infra/docs/HOSTINGER.md)** for the full deploy.
Clone this repo to `/opt/bd-coach`; the stack then lives at `/opt/bd-coach/infra`.

## Per-half docs

- [`config/README.md`](config/README.md) — behaviour layout, CI checks, persona setup, resilience parameters.
- [`infra/README.md`](infra/README.md) — full service table, first boot, DNS records, DR notes.

## CI

`.github/workflows/ci.yml` runs two jobs:

- **config** — JSON/YAML parse checks, yamllint, and the DLP regex tests.
- **infra** — Python syntax check on hooks/scripts, yamllint, and `docker compose config -q`.
