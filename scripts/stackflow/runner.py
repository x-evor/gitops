#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any


def _fatal(msg: str, code: int = 2) -> None:
    print(f"stackflow: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _load_yaml(path: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        _fatal(
            "missing dependency PyYAML. Install with: python3 -m pip install -r scripts/stackflow/requirements.txt"
        )
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        _fatal(f"config must be a YAML mapping, got {type(data).__name__}")
    return data


def _get(d: dict[str, Any], key: str, typ: type, *, required: bool = True) -> Any:
    v = d.get(key)
    if v is None:
        if required:
            _fatal(f"missing required field: {key}")
        return None
    if not isinstance(v, typ):
        _fatal(f"field {key} must be {typ.__name__}, got {type(v).__name__}")
    return v


def _as_str(v: Any, ctx: str) -> str:
    if not isinstance(v, str) or not v.strip():
        _fatal(f"{ctx} must be a non-empty string")
    return v


def _normalize_record(rec: dict[str, Any]) -> dict[str, Any]:
    name = rec.get("name")
    rtype = rec.get("type")
    if name is None or rtype is None:
        _fatal("dns.records entries require name and type")
    name = _as_str(name, "dns.records[].name")
    rtype = _as_str(rtype, "dns.records[].type").upper()

    out: dict[str, Any] = {"name": name, "type": rtype}

    if "valueFrom" in rec:
        out["valueFrom"] = _as_str(rec["valueFrom"], "dns.records[].valueFrom")
    elif "value" in rec:
        out["value"] = _as_str(rec["value"], "dns.records[].value")
    else:
        _fatal("dns.records entries require either value or valueFrom")

    ttl = rec.get("ttl")
    if ttl is not None:
        if not isinstance(ttl, int) or ttl <= 0:
            _fatal("dns.records[].ttl must be a positive int")
        out["ttl"] = ttl

    proxied = rec.get("proxied")
    if proxied is not None:
        if not isinstance(proxied, bool):
            _fatal("dns.records[].proxied must be boolean")
        out["proxied"] = proxied

    return out


@dataclass(frozen=True)
class Stack:
    name: str
    root_domain: str
    dns_provider: str
    cloud: str
    targets: list[dict[str, Any]]


def validate(cfg: dict[str, Any]) -> Stack:
    kind = _get(cfg, "kind", str)
    if kind != "StackFlow":
        _fatal(f"kind must be StackFlow, got {kind!r}")

    md = _get(cfg, "metadata", dict)
    name = _as_str(md.get("name"), "metadata.name")

    g = _get(cfg, "global", dict)
    root_domain = _as_str(g.get("domain"), "global.domain")
    dns_provider = _as_str(g.get("dns_provider"), "global.dns_provider")
    cloud = _as_str(g.get("cloud"), "global.cloud")

    # Optional multi-environment overrides.
    environments = g.get("environments")
    if environments is not None and not isinstance(environments, dict):
        _fatal("global.environments must be a mapping of env -> overrides")

    targets = _get(cfg, "targets", list)
    for i, t in enumerate(targets):
        if not isinstance(t, dict):
            _fatal(f"targets[{i}] must be a mapping")
        _as_str(t.get("id"), f"targets[{i}].id")
        _as_str(t.get("type"), f"targets[{i}].type")
        domains = t.get("domains")
        if domains is None or not isinstance(domains, list) or not domains:
            _fatal(f"targets[{i}].domains must be a non-empty list")
        for j, d in enumerate(domains):
            fqdn = _as_str(d, f"targets[{i}].domains[{j}]")
            if not (fqdn == root_domain or fqdn.endswith("." + root_domain)):
                _fatal(
                    f"targets[{i}].domains[{j}] must be under global.domain ({root_domain}), got {fqdn}"
                )

        dns = t.get("dns", {})
        if dns is None:
            dns = {}
        if not isinstance(dns, dict):
            _fatal(f"targets[{i}].dns must be a mapping")
        recs = dns.get("records", [])
        if recs is None:
            recs = []
        if not isinstance(recs, list):
            _fatal(f"targets[{i}].dns.records must be a list")
        for k, r in enumerate(recs):
            if not isinstance(r, dict):
                _fatal(f"targets[{i}].dns.records[{k}] must be a mapping")
            _normalize_record(r)

    return Stack(
        name=name,
        root_domain=root_domain,
        dns_provider=dns_provider,
        cloud=cloud,
        targets=targets,
    )


def _apply_env_overrides(cfg: dict[str, Any], env_name: str | None) -> dict[str, Any]:
    if env_name is None:
        return cfg
    g = cfg.get("global")
    if not isinstance(g, dict):
        return cfg
    envs = g.get("environments")
    if envs is None:
        return cfg
    if not isinstance(envs, dict):
        _fatal("global.environments must be a mapping of env -> overrides")
    overrides = envs.get(env_name)
    if overrides is None:
        _fatal(f"env not found in global.environments: {env_name}")
    if not isinstance(overrides, dict):
        _fatal(f"global.environments.{env_name} must be a mapping")

    # Shallow-merge global overrides into global.
    merged = dict(cfg)
    merged_global = dict(g)
    for k, v in overrides.items():
        merged_global[k] = v
    merged["global"] = merged_global
    return merged


def dns_plan(cfg: dict[str, Any], env_name: str | None) -> dict[str, Any]:
    cfg2 = _apply_env_overrides(cfg, env_name)
    stack = validate(cfg2)
    out: dict[str, Any] = {
        "stack": stack.name,
        "env": env_name or "",
        "global": {
            "domain": stack.root_domain,
            "dns_provider": stack.dns_provider,
        },
        "records": [],
    }

    # Flatten all explicit dns.records across targets.
    records: list[dict[str, Any]] = []
    for t in stack.targets:
        tid = t["id"]
        dns = t.get("dns") or {}
        recs = dns.get("records") or []
        for r in recs:
            nr = _normalize_record(r)
            nr["target"] = tid
            records.append(nr)
    out["records"] = records
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="stackflow")
    ap.add_argument("--config", required=True, help="Path to StackFlow YAML")
    ap.add_argument(
        "--env",
        default="",
        help="Optional environment name under global.environments (e.g. dev/prod)",
    )
    ap.add_argument(
        "--phase",
        required=True,
        choices=["validate", "dns-plan"],
        help="Which phase to run",
    )
    ap.add_argument(
        "--format",
        default="json",
        choices=["json"],
        help="Output format for plan phases",
    )
    args = ap.parse_args(argv)

    if not os.path.exists(args.config):
        _fatal(f"config not found: {args.config}")

    cfg = _load_yaml(args.config)
    env_name = args.env.strip() or None

    if args.phase == "validate":
        cfg2 = _apply_env_overrides(cfg, env_name)
        s = validate(cfg2)
        print(
            json.dumps(
                {
                    "ok": True,
                    "stack": s.name,
                    "env": env_name or "",
                    "domain": s.root_domain,
                    "dns_provider": s.dns_provider,
                    "cloud": s.cloud,
                    "targets": len(s.targets),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.phase == "dns-plan":
        plan = dns_plan(cfg, env_name)
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0

    _fatal(f"unknown phase: {args.phase}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
