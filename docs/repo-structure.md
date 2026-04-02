# Repository Structure

This repository contains declarative GitOps assets only. Below is a short overview of the key directories.

| Directory | Purpose |
|-----------|---------|
| `apps` | Flux HelmRelease and Kustomize files for applications. |
| `clusters` | Kustomize overlays for different clusters referencing the `apps` definitions. |
| `infra` | Platform and infrastructure declarations managed by Flux. |
| `scripts` | Utility scripts that support validation or operational workflows. |
| `config` | Non-sensitive configuration references and examples. |
| `docs` | Additional documentation. |
