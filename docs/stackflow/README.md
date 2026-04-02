# StackFlow (GitOps YAML Flow)

StackFlow is a declarative YAML describing a full business stack deployment
across DNS, cloud resources (IAC), and GitOps-driven delivery.

This repository already contains:
- `iac-template/` (Terraform reference templates)
- `.github/workflows/` (bootstrap workflows)

StackFlow adds a top-level config file that can drive those pieces in one place.

## Goals

- One YAML describes root domain + targets (Vercel, Cloud Run, vhosts, etc.)
- CI can validate config, produce a DNS plan, then apply phases later
- Never commit real secrets (tokens/keys); use GitHub Secrets / Secret Manager

## Config Example

See: `StackFlow/svc-plus.yaml`

## Schema (v1alpha1)

Top-level:
- `apiVersion`: `gitops.svc.plus/v1alpha1`
- `kind`: `StackFlow`
- `metadata.name`: stack id
- `global.domain`: root domain, e.g. `svc.plus`
- `global.dns_provider`: `cloudflare` (planned), `alicloud` (legacy)
- `global.cloud`: `gcp`
- `targets[]`: list of deployable targets

Target fields (common):
- `id`: unique id
- `type`: `vercel` | `cloud-run` | `vhost` | `kubernetes` (planned)
- `domains[]`: FQDNs owned by this target
- `dns.records[]`: explicit DNS record intents

DNS record intent:
- `name`: record name relative to `global.domain` (e.g. `www`)
- `type`: `A` | `AAAA` | `CNAME` | `TXT` | `MX`
- `value`: literal value (string)
- `valueFrom`: dotted path reference inside the target (e.g. `endpoints.public_ipv4`)
- `ttl`: optional int seconds
- `proxied`: optional bool (Cloudflare-specific)

## Workflows

Planned phases:
- `validate`: validate YAML structure
- `dns-plan`: output required DNS records (no apply)
- `dns-apply`: apply DNS changes (provider-specific)
- `iac-apply`: provision resources via Terraform
- `deploy`: deploy apps via GitOps or repo-dispatch
- `observe`: connect monitoring / alerts

Today we only ship `validate` + `dns-plan` as the first step.
