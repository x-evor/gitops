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
The ingress domain is `postgresql-prod.svc.plus` for this prod cluster. TLS for
`postgresql-tls` is now owned directly by cert-manager in both the `platform`
and `database` namespaces, so `stunnel-server` can mount the database-local
Secret without any cross-namespace sync job.

Default certificate issuance uses ACME HTTP-01 through the `caddy` ingress
class. A DNS-01 Cloudflare issuer is predeclared for future wildcard and
additional subdomain certificates, and `selfSigned` remains available for
internal temporary or fallback use.

The boundary is intentionally narrow:

- `cert-manager` owns the TLS Secret lifecycle
- `Caddy` provides ingress routing and HTTP-01 challenge reachability
- `external-dns` only reconciles DNS records
- `external-secrets` continues to manage Vault-backed runtime secrets
