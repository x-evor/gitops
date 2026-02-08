#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from ansible.module_utils.basic import AnsibleModule


API_BASE = "https://api.cloudflare.com/client/v4"


def _request(method, path, api_token, payload=None, query=None):
    url = API_BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query)

    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url=url, data=body, method=method)
    req.add_header("Authorization", "Bearer " + api_token)
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


def _api_ok(data):
    return isinstance(data, dict) and data.get("success") is True


def _api_first_result(data):
    if not _api_ok(data):
        return None
    res = data.get("result")
    if isinstance(res, list) and res:
        return res[0]
    return None


def _zone_id(api_token, zone_name):
    data = _request("GET", "/zones", api_token, query={"name": zone_name, "per_page": 50})
    z = _api_first_result(data)
    if not z:
        return None
    return z.get("id")


def _record_fqdn(zone, rr):
    rr = rr.strip()
    if rr in ("@", zone):
        return zone
    return rr + "." + zone


def _get_record(api_token, zone_id, record_type, fqdn):
    data = _request(
        "GET",
        f"/zones/{zone_id}/dns_records",
        api_token,
        query={"type": record_type, "name": fqdn, "per_page": 50},
    )
    return _api_first_result(data)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            zone=dict(type="str", required=True),
            rr=dict(type="str", required=True),
            type=dict(type="str", required=True),
            value=dict(type="str"),
            ttl=dict(type="int", default=1),
            proxied=dict(type="bool", default=False),
            priority=dict(type="int", required=False),
            api_token=dict(type="str", required=True, no_log=True),
        ),
        supports_check_mode=True,
    )

    state = module.params["state"]
    zone = module.params["zone"]
    rr = module.params["rr"]
    record_type = module.params["type"].upper()
    value = module.params["value"]
    ttl = module.params["ttl"]
    proxied = module.params["proxied"]
    priority = module.params.get("priority", None)
    api_token = module.params["api_token"]

    if state == "present" and not value:
        module.fail_json(msg="value is required when state=present")

    try:
        zid = _zone_id(api_token, zone)
    except Exception as e:
        module.fail_json(msg=f"Failed to query Cloudflare zone id: {e}")

    if not zid:
        module.fail_json(msg=f"Cloudflare zone not found: {zone}")

    fqdn = _record_fqdn(zone, rr)

    try:
        existing = _get_record(api_token, zid, record_type, fqdn)
    except Exception as e:
        module.fail_json(msg=f"Failed to query Cloudflare DNS record: {e}")

    # ----------------------------
    # ABSENT
    # ----------------------------
    if state == "absent":
        if not existing:
            module.exit_json(changed=False, msg="Record already absent")
        if module.check_mode:
            module.exit_json(changed=True)
        rid = existing.get("id")
        try:
            data = _request("DELETE", f"/zones/{zid}/dns_records/{rid}", api_token)
        except Exception as e:
            module.fail_json(msg=f"Failed to delete record: {e}")
        if not _api_ok(data):
            module.fail_json(msg="Cloudflare API error deleting record", details=data)
        module.exit_json(changed=True, msg="Record deleted", record_id=rid, fqdn=fqdn)

    # ----------------------------
    # PRESENT (create/update)
    # ----------------------------
    desired = {
        "type": record_type,
        "name": fqdn,
        "content": value,
        "ttl": ttl,
        "proxied": proxied,
    }
    if priority is not None:
        desired["priority"] = priority

    if existing:
        cur = {
            "type": existing.get("type"),
            "name": existing.get("name"),
            "content": existing.get("content"),
            "ttl": existing.get("ttl"),
            "proxied": existing.get("proxied"),
        }
        if priority is not None:
            cur["priority"] = existing.get("priority")

        if cur == desired:
            module.exit_json(
                changed=False,
                msg="Record already up to date",
                record_id=existing.get("id"),
                fqdn=fqdn,
            )

        if module.check_mode:
            module.exit_json(changed=True)

        rid = existing.get("id")
        try:
            data = _request("PUT", f"/zones/{zid}/dns_records/{rid}", api_token, payload=desired)
        except Exception as e:
            module.fail_json(msg=f"Failed to update record: {e}")
        if not _api_ok(data):
            module.fail_json(msg="Cloudflare API error updating record", details=data)
        module.exit_json(changed=True, msg="Record updated", record_id=rid, fqdn=fqdn)

    # CREATE
    if module.check_mode:
        module.exit_json(changed=True)

    try:
        data = _request("POST", f"/zones/{zid}/dns_records", api_token, payload=desired)
    except Exception as e:
        module.fail_json(msg=f"Failed to create record: {e}")
    if not _api_ok(data):
        module.fail_json(msg="Cloudflare API error creating record", details=data)

    rec = data.get("result") or {}
    module.exit_json(changed=True, msg="Record created", record_id=rec.get("id"), fqdn=fqdn)


if __name__ == "__main__":
    main()

