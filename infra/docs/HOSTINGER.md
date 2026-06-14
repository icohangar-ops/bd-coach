# Deploy BD Coach on Hostinger VPS

Hostinger KVM VPS works well for this stack. No GPU — Ollama runs on CPU, or use Groq for faster responses.

## Plan sizing

| Hostinger plan | RAM | Recommendation |
|---|---|---|
| KVM 2 | 8 GB | **Slim profile** + `GROQ_API_KEY` required for usable chat speed |
| KVM 4 | 16 GB | Full stack with CPU Ollama (`llama3.2:3b` / `mistral:7b`) |
| KVM 8 | 32 GB | Full stack + larger local models (`llama3.1:8b`) |

The full compose runs ~18 containers. On 8 GB, use the slim overlay to skip Grafana, Prometheus, OpenObserve, Rasa, and Whisper until you upgrade.

---

## 1. Server prep (one time)

SSH in as root:

```bash
ssh root@YOUR_VPS_IP
```

From your laptop, copy the install script or clone the repo first:

```bash
# On the VPS after cloning to /opt/bd-coach:
cd /opt/bd-coach/infra
chmod +x scripts/install-hostinger.sh
./scripts/install-hostinger.sh
```

This installs Docker, configures UFW (22, 80, 443), adds a 4 GB swap file, and creates user `bdcoach`.

---

## 2. DNS (Hostinger hPanel or external registrar)

Create **A records** pointing to your VPS IP:

| Host | Points to |
|---|---|
| `chat` | VPS IP |
| `bd-coach` | VPS IP |
| `n8n` | VPS IP |
| `auth` | VPS IP |
| `files` | VPS IP |
| `data` | VPS IP |
| `api` | VPS IP |
| `minio` | VPS IP |

If your domain is `example.com`, set in `.env`:

```
BD_COACH_DOMAIN=example.com
```

Traefik will issue Let's Encrypt certs automatically once DNS propagates (usually 5–30 min).

**Hostinger firewall:** In hPanel → VPS → Security → Firewall, allow inbound **TCP 80** and **443** in addition to SSH.

---

## 3. Configure environment

```bash
su - bdcoach
cd /opt/bd-coach/infra
cp .env.example .env
nano .env
```

Minimum required:

```bash
BD_COACH_DOMAIN=yourdomain.com
ACME_EMAIL=you@yourdomain.com

# Generate: openssl rand -hex 32
PG_PASSWORD=
N8N_ENCRYPTION_KEY=
LITELLM_MASTER_KEY=
VAULT_ROOT_TOKEN=
MINIO_ROOT_PASSWORD=
KEYCLOAK_ADMIN_PASSWORD=
KEYCLOAK_LIBRECHAT_SECRET=    # match keycloak/realm-export.json client secret after edit
BASEROW_SECRET_KEY=
NEXTCLOUD_ADMIN_PASSWORD=
OO_PASSWORD=
GRAFANA_PASSWORD=

# Required on Hostinger (no GPU) — uses config.hostinger.yaml (Groq primary):
GROQ_API_KEY=gsk_...
```

With the Hostinger compose overlay, LiteLLM routes:
- **CEO** → Groq `llama-3.3-70b-versatile`
- **BDs** → Groq `llama-3.1-8b-instant`
- **Fallback** → local Ollama if Groq is down

Edit `keycloak/realm-export.json`:

- Replace `example.com` in redirect URIs with your domain
- Set `librechat` client `secret` to match `KEYCLOAK_LIBRECHAT_SECRET`
- Change default user passwords from `CHANGE_ME`

---

## 4. Start the stack

**16 GB+ RAM:**

```bash
docker compose \
  -f compose/docker-compose.yml \
  -f compose/docker-compose.hostinger.yml \
  up -d
```

**8 GB RAM (slim):**

```bash
docker compose \
  -f compose/docker-compose.yml \
  -f compose/docker-compose.hostinger.yml \
  -f compose/docker-compose.slim.yml \
  up -d
```

Watch startup:

```bash
docker compose -f compose/docker-compose.yml logs -f traefik keycloak librechat
```

---

## 5. Bootstrap

```bash
./scripts/bootstrap.sh
```

On slim/CPU hosts, pull smaller models:

```bash
docker compose -f compose/docker-compose.yml exec ollama ollama pull llama3.2:3b
docker compose -f compose/docker-compose.yml exec ollama ollama pull mistral:7b
```

Update `litellm/config.yaml` model names if you use `llama3.2:3b` instead of `llama3.1:8b`.

---

## 6. Mattermost (you host this)

1. Open `https://chat.yourdomain.com` — create admin account on first visit
2. Create private channel `bd-ops`
3. Integrations → Incoming Webhooks → create hooks for F1, F3, F4, F7, CEO digest
4. Paste URLs into `.env` as `MM_HOOK_F1`, etc., then `docker compose ... up -d` to reload n8n

---

## 7. Baserow + Nextcloud

| Service | URL | Setup |
|---|---|---|
| Baserow | `https://data.yourdomain.com` | Create workspace → tables: `bd_pipeline`, `activity_log`, `weekly_reports`, `scorecard`, `commission` → copy table IDs to `.env` |
| Nextcloud | `https://files.yourdomain.com` | Create folders under `/BD/` per bootstrap output |

---

## 8. Import n8n flows

1. `https://n8n.yourdomain.com`
2. Settings → Import → `n8n-flows/flows/*.json`
3. Add SMTP credential + activate flows

---

## 9. Verify

| Check | URL |
|---|---|
| LibreChat login | `https://bd-coach.yourdomain.com` |
| Keycloak admin | `https://auth.yourdomain.com` |
| DLP tests (on laptop) | `python config/dlp/run_tests.py` |

Log in as `ceo@example.org` (or your Keycloak users) via OIDC.

---

## Troubleshooting

**Certs not issuing** — DNS not propagated, or port 443 blocked in hPanel firewall.

**Ollama OOM** — use slim profile + Groq failover; or upgrade to KVM 4.

**High memory** — `docker stats`; stop observability: add `-f compose/docker-compose.slim.yml`.

**Keycloak redirect error** — redirect URI in realm JSON must exactly match `https://bd-coach.${BD_COACH_DOMAIN}/oauth/openid/callback`.

---

## CI deploy to this VPS

Add GitHub secrets:

- `DEPLOY_HOST` — VPS IP or hostname
- `DEPLOY_USER` — `bdcoach`
- `DEPLOY_SSH_KEY` — private key for `bdcoach@host`

Workflow SSH target: `/opt/bd-coach` (clone monorepo or three repos into that path).
