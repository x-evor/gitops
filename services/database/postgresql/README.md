# PostgreSQL GitOps Bootstrap

This stack uses ExternalSecrets to materialize runtime credentials from Vault.
The GitOps manifests intentionally do not store secret values.

## Vault paths expected by this stack

- `postgresql.svc.plus`
  - `POSTGRES_USER`
  - `POSTGRES_PASSWORD`
  - `GHCR_USERNAME`
  - `GHCR_TOKEN`
## Bootstrap rule

Before or during initial reconciliation, the Vault key `postgresql.svc.plus`
must be seeded with the runtime credentials expected by the manifests in this
directory. Otherwise the ExternalSecrets controller will report
`Secret does not exist`.

## Helper

Use `scripts/seed-vault-postgresql.sh` from a trusted admin shell to write the
expected Vault keys from local environment variables or existing K8s Secrets.
The ingress domain is `postgresql-prod.svc.plus` for this prod cluster. The shared TLS Secret for `postgresql-tls` is synchronized by the
`platform/postgresql-tls-sync` GitOps CronJob into `database/postgresql-tls`, which
`stunnel-server` consumes directly. Do not commit the secret values to Git.
