#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

import yaml


API_BASE = "https://api.cloudflare.com/client/v4"


def _req(method: str, path: str, token: str, payload=None, query=None):
    url = API_BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url=url, data=body, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _ok(d):
    return isinstance(d, dict) and d.get("success") is True


def zone_id(token: str, zone_name: str) -> str:
    d = _req("GET", "/zones", token, query={"name": zone_name, "per_page": 50})
    if not _ok(d) or not d.get("result"):
        raise RuntimeError(f"zone not found: {zone_name}")
    return d["result"][0]["id"]


def fqdn(zone: str, rr: str) -> str:
    rr = rr.strip()
    if rr in ("@", zone):
        return zone
    return rr + "." + zone


def get_record(token: str, zid: str, rtype: str, name: str):
    d = _req("GET", f"/zones/{zid}/dns_records", token, query={"type": rtype, "name": name, "per_page": 50})
    if not _ok(d):
        raise RuntimeError("query dns_records failed")
    res = d.get("result") or []
    return res[0] if res else None


def ensure_record(token: str, zid: str, zone: str, rec: dict):
    rr = rec["rr"]
    rtype = rec["type"].upper()
    value = rec["value"]
    ttl = int(rec.get("ttl", 1))
    proxied = bool(rec.get("proxied", False))
    priority = rec.get("priority", None)

    name = fqdn(zone, rr)
    desired = {"type": rtype, "name": name, "content": value, "ttl": ttl, "proxied": proxied}
    if priority is not None:
        desired["priority"] = int(priority)

    cur = get_record(token, zid, rtype, name)
    if not cur:
        print("CREATE:", desired)
        d = _req("POST", f"/zones/{zid}/dns_records", token, payload=desired)
        if not _ok(d):
            raise RuntimeError("create failed: " + json.dumps(d))
        return

    cur_slim = {
        "type": cur.get("type"),
        "name": cur.get("name"),
        "content": cur.get("content"),
        "ttl": cur.get("ttl"),
        "proxied": cur.get("proxied"),
    }
    if priority is not None:
        cur_slim["priority"] = cur.get("priority")

    if cur_slim == desired:
        print("OK:", desired["name"], desired["type"])
        return

    print("UPDATE:", desired)
    rid = cur["id"]
    d = _req("PUT", f"/zones/{zid}/dns_records/{rid}", token, payload=desired)
    if not _ok(d):
        raise RuntimeError("update failed: " + json.dumps(d))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {sys.argv[0]} <dns_records.yaml>", file=sys.stderr)
        return 2
    fn = argv[1]
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        print("CLOUDFLARE_API_TOKEN is required", file=sys.stderr)
        return 2

    cfg = yaml.safe_load(open(fn, "r", encoding="utf-8")) or {}
    for zone, recs in cfg.items():
        zid = zone_id(token, zone)
        for rec in recs or []:
            ensure_record(token, zid, zone, rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

