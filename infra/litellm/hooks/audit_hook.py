"""Audit hook — writes every LLM call's metadata directly to Postgres ``audit.events``.

Replaces the previous file-based JSONL logging. Records are inserted through an
``asyncpg`` connection pool. To ensure audit records survive transient DB
outages (and are not lost on container restart), failed inserts are appended to
a durable on-disk spool. The spool is written atomically and drained back into
Postgres on the next successful connection, so no event is dropped while the
database is briefly unreachable.

Configuration (env):
    AUDIT_DATABASE_URL  asyncpg DSN for the ``audit`` database, e.g.
                        postgres://bdcoach:PASS@postgres:5432/audit
    AUDIT_SPOOL_PATH    optional override for the spool file location
                        (default: /var/log/bd-coach/audit_spool.jsonl)
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

from cubiczan_resilience import atomic_write, resilient
from litellm.integrations.custom_logger import CustomLogger

try:
    import asyncpg
except ImportError:  # pragma: no cover - asyncpg is a runtime dependency in the image
    asyncpg = None  # type: ignore[assignment]

_SPOOL_PATH = os.environ.get(
    "AUDIT_SPOOL_PATH", "/var/log/bd-coach/audit_spool.jsonl"
)
_INSERT_SQL = (
    "INSERT INTO audit.events (event, persona, meta) VALUES ($1, $2, $3::jsonb)"
)


class AuditHook(CustomLogger):
    def __init__(self) -> None:
        self._pool: Optional["asyncpg.Pool"] = None
        self._pool_lock = asyncio.Lock()
        # Serialise spool I/O so concurrent failures don't interleave writes.
        self._spool_lock = asyncio.Lock()

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        persona = (kwargs.get("litellm_params") or {}).get("metadata", {}).get("persona", "UNKNOWN")
        await self._record(
            event="llm.call",
            persona=persona,
            meta={
                "ts": time.time(),
                "model": kwargs.get("model"),
                "latency_ms": int((end_time - start_time).total_seconds() * 1000),
            },
        )

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        persona = (kwargs.get("litellm_params") or {}).get("metadata", {}).get("persona", "UNKNOWN")
        await self._record(
            event="llm.error",
            persona=persona,
            meta={
                "ts": time.time(),
                "model": kwargs.get("model"),
                "error": str(response_obj),
            },
        )

    # -- core ---------------------------------------------------------------

    async def _record(self, event: str, persona: str, meta: Dict[str, Any]) -> None:
        """Persist one audit event, never raising into the LiteLLM call path."""
        record = {"event": event, "persona": persona, "meta": meta}
        try:
            await self._drain_spool()
            await self._insert(event, persona, meta)
        except Exception:
            # DB unreachable or insert failed: spool durably so nothing is lost.
            await self._spool(record)

    @resilient(timeout=5.0, max_attempts=3)
    async def _insert(self, event: str, persona: str, meta: Dict[str, Any]) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(_INSERT_SQL, event, persona, json.dumps(meta))

    async def _get_pool(self) -> "asyncpg.Pool":
        if self._pool is not None:
            return self._pool
        async with self._pool_lock:
            if self._pool is None:
                if asyncpg is None:
                    raise RuntimeError("asyncpg is not installed")
                dsn = os.environ.get("AUDIT_DATABASE_URL")
                if not dsn:
                    raise RuntimeError("AUDIT_DATABASE_URL is not set")
                self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=4)
        return self._pool

    # -- durable spool (buffer/retry queue) ---------------------------------

    async def _spool(self, record: Dict[str, Any]) -> None:
        async with self._spool_lock:
            existing = self._read_spool()
            existing.append(record)
            self._write_spool(existing)

    async def _drain_spool(self) -> None:
        """Replay any spooled records into Postgres, then truncate the spool.

        Runs before each new insert. If the DB is still down the insert raises
        and the caller re-spools, so records persist across container restarts.
        """
        async with self._spool_lock:
            pending = self._read_spool()
            if not pending:
                return
            remaining: List[Dict[str, Any]] = []
            for i, rec in enumerate(pending):
                try:
                    await self._insert(rec["event"], rec["persona"], rec["meta"])
                except Exception:
                    # Keep this and all later records; preserve ordering.
                    remaining = pending[i:]
                    self._write_spool(remaining)
                    raise
            # All replayed: clear the spool.
            self._write_spool([])

    @staticmethod
    def _read_spool() -> List[Dict[str, Any]]:
        if not os.path.exists(_SPOOL_PATH):
            return []
        records: List[Dict[str, Any]] = []
        with open(_SPOOL_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except ValueError:
                        continue
        return records

    @staticmethod
    def _write_spool(records: List[Dict[str, Any]]) -> None:
        data = "".join(json.dumps(r) + "\n" for r in records)
        atomic_write(_SPOOL_PATH, data)
