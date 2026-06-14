# BD Coach — config/

(Formerly the `bd-coach-config` repo; now the config half of the unified `bd-coach` repo.)

Version-controlled agent behaviour. PR-required changes to prompt, personas, DLP, and topics.

## Layout

```
prompts/     Master system prompt (locked)
personas/    CEO / USA_BD / EU_BD scopes → Keycloak groups
topics/      15 Rasa intents + LibreChat tool mapping
dlp/         HR/compensation regex rules + CI tests
cards/       Adaptive card JSON templates
knowledge/   Connector manifest (Baserow, Nextcloud, Whisper)
```

## CI checks

- `python dlp/run_tests.py` — regex fixtures must pass
- yamllint on all YAML
- CODEOWNERS review on `prompts/`, `personas/`, `dlp/`

## Resilience & action safety

### Adaptive card idempotency (`cards/`)

Every `Action.Submit` payload carries an `idempotency_key` field (bound to
`${idempotencyKey}`, minted per-card-instance by the runtime). The consuming
runtime **must validate this key server-side before executing the verb**:

- Persist seen keys in an idempotency store (the
  [`cubiczan-resilience`](https://github.com/icohangar-ops/cubiczan-resilience)
  `IdempotencyStore`, in-memory or file-backed).
- On submit, reject/short-circuit any verb whose `idempotency_key` was already
  recorded — this prevents double-execution of money/state verbs
  (`email_commission_pdf`, `submit_weekly`, `notify_ceo`, `mark_dormant`,
  `discard_weekly`, …) from retries, double-clicks, or replayed payloads.
- The key doubles as a CSRF/replay guard: a verb with a missing or unknown key
  must fail closed rather than execute.

### Knowledge-source resilience parameters (`knowledge/sources.yaml`)

Each connector entry defines machine-readable resilience parameters so the
runtime never falls back to implicit (possibly nonexistent) defaults:

| Field | Meaning | Default |
|---|---|---|
| `timeout_s` | Per-request timeout in seconds | `10` |
| `max_retries` | Retry attempts on failure | `2` |
| `retry_backoff_s` | Base backoff between retries (seconds) | `1.0` |
| `fallback` | Degraded behaviour when retries exhaust (`last_known_good`, `cached_index`, `queue_for_retry`, `skip`) | — |

Long-running connectors (e.g. Whisper transcription) carry larger timeouts.
The runtime should drive its HTTP/RPC clients (e.g. via the
`cubiczan-resilience` `@resilient` decorator) from these values.

## Persona setup

Map Keycloak groups to personas in `personas/personas.yaml`:

| Group | Persona |
|---|---|
| `ceo` | CEO |
| `bd-usa` | USA_BD |
| `bd-eu` | EU_BD |

Default demo users ship in `infra/keycloak/realm-export.json` — change passwords before production.
