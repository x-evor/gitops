#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  seed-vault-postgresql.sh --vault-addr <addr> --vault-token <token> \
    --postgres-user <user> --postgres-password <password> \
  --ghcr-username <user> --ghcr-token <token> \
  --tls-crt <path> --tls-key <path>

Options may also be provided via environment variables:
  VAULT_ADDR, VAULT_TOKEN, POSTGRES_USER, POSTGRES_PASSWORD,
  GHCR_USERNAME, GHCR_TOKEN, TLS_CRT, TLS_KEY

This writes the runtime values expected by databases/postgresql/*.yaml to the
Vault KV path postgresql.svc.plus and the shared TLS material for
postgresql-vultr.svc.plus.
EOF
}

VAULT_ADDR="${VAULT_ADDR:-}"
VAULT_TOKEN="${VAULT_TOKEN:-}"
POSTGRES_USER="${POSTGRES_USER:-}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
GHCR_USERNAME="${GHCR_USERNAME:-}"
GHCR_TOKEN="${GHCR_TOKEN:-}"
TLS_CRT="${TLS_CRT:-}"
TLS_KEY="${TLS_KEY:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vault-addr) VAULT_ADDR="${2:-}"; shift 2 ;;
    --vault-token) VAULT_TOKEN="${2:-}"; shift 2 ;;
    --postgres-user) POSTGRES_USER="${2:-}"; shift 2 ;;
    --postgres-password) POSTGRES_PASSWORD="${2:-}"; shift 2 ;;
    --ghcr-username) GHCR_USERNAME="${2:-}"; shift 2 ;;
    --ghcr-token) GHCR_TOKEN="${2:-}"; shift 2 ;;
    --tls-crt) TLS_CRT="${2:-}"; shift 2 ;;
    --tls-key) TLS_KEY="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

missing=0
for name in VAULT_ADDR VAULT_TOKEN POSTGRES_USER POSTGRES_PASSWORD GHCR_USERNAME GHCR_TOKEN TLS_CRT TLS_KEY; do
  if [[ -z "${!name}" ]]; then
    echo "missing required value: $name" >&2
    missing=1
  fi
done
[[ "$missing" -eq 0 ]] || exit 1

if ! command -v vault >/dev/null 2>&1; then
  echo "missing required command: vault" >&2
  exit 1
fi

export VAULT_ADDR VAULT_TOKEN

vault kv put postgresql.svc.plus \
  POSTGRES_USER="$POSTGRES_USER" \
  POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  GHCR_USERNAME="$GHCR_USERNAME" \
  GHCR_TOKEN="$GHCR_TOKEN"

vault kv put postgresql-vultr.svc.plus \
  tls.crt="$(cat "$TLS_CRT")" \
  tls.key="$(cat "$TLS_KEY")"
