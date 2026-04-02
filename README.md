# Cloud-Neutral Toolkit GitOps

This repository is the GitOps declaration layer for the Cloud-Neutral Toolkit.

## Scope

- Store declarative Kubernetes resources, Flux Kustomizations, and non-sensitive multi-environment values.
- Keep application charts and Helm templates in the dedicated chart repository.
- Keep imperative automation such as Ansible playbooks and inventories out of this repository.

## Layout

- `infra/`: platform, infrastructure, and shared service declarations
- `apps/`: application release declarations
- `clusters/`: cluster-level overlays and entrypoints
- `docs/`: repository conventions and operational documentation

For a quick structure overview, see [docs/repo-structure.md](docs/repo-structure.md).
