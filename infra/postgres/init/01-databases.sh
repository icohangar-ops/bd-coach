#!/bin/bash
set -e

for db in librechat n8n mattermost audit keycloak baserow litellm nextcloud; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE $db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
EOSQL
done

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname audit <<-EOSQL
  CREATE TABLE IF NOT EXISTS audit.events (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    event       TEXT NOT NULL,
    persona     TEXT,
    topic       TEXT,
    payload_hash TEXT,
    meta        JSONB
  );
  CREATE TABLE IF NOT EXISTS audit.flow_runs (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    flow_id     TEXT NOT NULL,
    status      TEXT NOT NULL,
    meta        JSONB
  );
  CREATE TABLE IF NOT EXISTS audit.flow_dlq (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    flow_id     TEXT NOT NULL,
    error       TEXT,
    payload     JSONB
  );
  REVOKE DELETE, UPDATE ON audit.events FROM PUBLIC;
EOSQL
