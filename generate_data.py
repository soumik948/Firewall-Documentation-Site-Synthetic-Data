"""
Sentrywall demo-site data generator.

Pulls the SAME synthetic register the 272-test suite runs against
(test_sentrywall_core.estate()) and shapes it into the JSON the static
"Firewall Documentation System" clone reads. Nothing here is invented data
for the hosts/rules — it's the tested fixture, reformatted for the UI.
Firewall-device inventory (names, interfaces, routing) is UI dressing only
(clearly synthetic, btnl-demo namespace) — the underlying hosts/rules/zones
it displays are the real tested fixture.

Run: python3 generate_data.py   -> writes data.json next to this script.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from test_sentrywall_core import estate  # noqa: E402

ZONE_COLOR = {
    "MGMT": "#c9c9c9", "DMZ": "#7fe6e6", "WEB": "#7fe6e6",
    "APP": "#9fe08a", "DB": "#3fae4a", "CORE": "#3fae4a",
    "INTERNET": "#ffffff",
}


def svc_label(svc_list):
    out = []
    for proto, lo, hi in svc_list:
        if proto == "any" and lo == 0 and hi == 65535:
            out.append("any")
        elif lo == hi:
            out.append(f"{proto}/{lo}")
        else:
            out.append(f"{proto}/{lo}-{hi}")
    return ", ".join(out)


def build():
    reg, inv, groups, flows = estate()

    # core-derived /24 networks, so CIDR-containment lookup works for core IPs too, not just
    # exact host matches (dedup by /24 — several core hosts share one /24)
    import ipaddress as _ip
    seen_cidrs = {}
    for ip, h in inv.items():
        try:
            net24 = str(_ip.ip_network(f"{ip}/24", strict=False))
        except ValueError:
            continue  # skip IPv6 fixture entries here — extended layer is v4-only anyway
        if net24 not in seen_cidrs:
            seen_cidrs[net24] = {"cidr": net24, "name": f"DCN-{h.app}-{h.env}-CORE",
                                  "zone": h.zone, "env": h.env, "category": h.zone,
                                  "firewall": "", "interface": "", "comment": "",
                                  "tier": "core", "level": "subnet"}
    core_networks = list(seen_cidrs.values())
    cidrs_by_zone = {}
    for n in core_networks:
        cidrs_by_zone.setdefault(n["zone"], []).append(n["cidr"])

    hosts = []
    for ip, h in sorted(inv.items()):
        hosts.append({
            "ip": ip, "zone": h.zone, "env": h.env, "app": h.app,
            "tags": sorted(h.tags), "color": ZONE_COLOR.get(h.zone, "#eeeeee"),
        })

    def zone_of(token):
        if token in inv:
            return inv[token].zone
        return ""

    dc_devices = ["fwb-ahm1", "fwb-ber2", "fwf-ahr6", "fwf-ber6", "fwhid1", "fwoff1"]
    rules = []
    for i, r in enumerate(reg):
        rules.append({
            "rule_id": r.rule_id, "order": r.order, "action": r.action,
            "source": ", ".join(r.src), "source_zone": zone_of(r.src[0]) if r.src else "",
            "destination": ", ".join(r.dst), "destination_zone": zone_of(r.dst[0]) if r.dst else "",
            "service": svc_label(r.svc), "tags": sorted(r.tags),
            "schedule": r.schedule, "expires": r.expires,
            "firewall": dc_devices[i % len(dc_devices)],
            "comment": f"#{100000 + int(r.rule_id[1:])} synthetic",
        })

    objectgroups = [
        {"name": "g-QUARANTINE", "members": groups.get("g-QUARANTINE", []),
         "comment": "auto-quarantine placeholder group"},
        {"name": "G-BIL01-PROD-APP", "members": [ip for ip in inv if inv[ip].app == "BIL01"],
         "comment": "#100501 billing app tier, PROD"},
        {"name": "G-BIL01-PROD-DB", "members": [ip for ip in inv if inv[ip].app in ("BIL01-DB", "BIL01-DB-DR")],
         "comment": "#100502 billing DB tier incl. DR"},
        {"name": "G-CRM-WEB", "members": [ip for ip in inv if "CRM-WEB" in inv[ip].app],
         "comment": "#100503 CRM web tier, all envs"},
    ]

    # Firewall device inventory — synthetic UI dressing (btnl-demo namespace), grouped like the
    # real documentation system's Eplus / DC / OLD / Cloud sections.
    firewalls = {
        "DC": [
            {"id": "fwb-ahm1", "rules": 42, "zones": ["MGMT", "DMZ", "APP", "DB"]},
            {"id": "fwb-ber2", "rules": 31, "zones": ["MGMT", "APP"]},
            {"id": "fwf-ahr6", "rules": 18, "zones": ["MGMT", "WEB"]},
            {"id": "fwf-ber6", "rules": 27, "zones": ["MGMT", "DMZ"]},
            {"id": "fwhid1", "rules": 9, "zones": ["MGMT"]},
            {"id": "fwoff1", "rules": 15, "zones": ["MGMT", "APP"]},
        ],
        "OLD": [
            {"id": "fwber51", "rules": 6, "zones": ["MGMT"]},
            {"id": "fwdus1", "rules": 4, "zones": ["MGMT"]},
        ],
        "Cloud": [
            {"id": "fwaws1", "rules": 22, "zones": ["MGMT", "APP", "DB"]},
            {"id": "fwaws2", "rules": 19, "zones": ["MGMT", "APP"]},
            {"id": "fwgcp1", "rules": 14, "zones": ["MGMT", "DMZ"]},
        ],
    }

    # Interfaces/zones + routing for EVERY device — built from cidrs_by_zone (computed above
    # from the real inv), not hand-authored per device, so no device is left with "no data".
    RESPONSIBLE = ["n.schmidt@btnl-demo.local", "r.sharma@btnl-demo.local", "m.weber@btnl-demo.local"]
    interfaces, routing = {}, {}
    for cat, devices in firewalls.items():
        for idx, dev in enumerate(devices):
            fw_id = dev["id"]
            ifaces = [{"iface": "Mgmt", "subnet": "10.99.0.0/24", "zone": "MGMT",
                       "description": f"DCN-MGMT-{fw_id}", "responsible": RESPONSIBLE[idx % 3],
                       "comment": f"#{100010 + idx}"}]
            routes = [{"destination": "10.99.0.0/24", "gateway": "direct", "interface": "mgmt0"}]
            vlan = 400
            for zone in dev["zones"]:
                if zone == "MGMT":
                    continue  # already added as the base Mgmt interface above
                for cidr in cidrs_by_zone.get(zone, [])[:2]:
                    vlan += 1
                    iface_name = f"bond1.{vlan}"
                    ifaces.append({"iface": iface_name, "subnet": cidr, "zone": zone,
                                    "description": f"DCN-{zone}-{fw_id}",
                                    "responsible": RESPONSIBLE[idx % 3], "comment": f"#{100010 + vlan}"})
                    routes.append({"destination": cidr, "gateway": "direct", "interface": iface_name})
            routes.append({"destination": "0.0.0.0/0", "gateway": "10.99.0.1", "interface": "bond1.410"})
            interfaces[fw_id] = ifaces
            routing[fw_id] = routes

    # Zone-classification wizard — same Yes/No tree as the screenshots (independent of the
    # engine's enforcement-zone enum; this classifies a NEW system before it gets one).
    zone_wizard = {
        "start": "q_external",
        "nodes": {
            "q_external": {
                "q": "Does the system have connections to external systems?",
                "yes": "q_unknown_target", "no": "q_workstation_or_server",
            },
            "q_unknown_target": {
                "q": "Are there connections from or to unknown target systems?",
                "yes": {"result": "Zone A", "note": "Unknown external peers — highest scrutiny."},
                "no": "q_sensitive_data",
            },
            "q_sensitive_data": {
                "q": "Is sensitive data accessed?",
                "yes": {"result": "Zone B", "note": "e.g. proxy system / ALG, sensitive data in flight."},
                "no": {"result": "Zone B2", "note": "e.g. proxy system / ALG — no backend storage required."},
            },
            "q_workstation_or_server": {
                "q": "Is the system an office system (workstation) or a server?",
                "workstation": {"result": "Zone C", "note": "Office workstation, no external exposure."},
                "server": "q_data_used",
            },
            "q_data_used": {
                "q": "What is the system used for or which data is processed?",
                "prod": {"result": "Zone A2", "note": "Production server, internal only."},
                "test": {"result": "Zone C", "note": "Test system — productive data may not be used."},
                "dev": {"result": "Zone C", "note": "Dev system — productive data may not be used."},
            },
        },
    }

    search_grammar = (
        "expression = term { ['or' | '|'] term }\n"
        "term       = factor { ['and' | '&' | space] factor }\n"
        "factor     = [ '!' ] obj | '(' expression ')'\n"
        "obj        = [ spec ':' ] NAME\n"
        "spec       = 'src' | 'dst' | 'serv' | 'action' | 'fw'\n"
        "name       = [a-zA-Z][:alnum:]*"
    )

    return {
        "networks": core_networks,
        "hosts": hosts, "rules": rules, "objectgroups": objectgroups,
        "firewalls": firewalls, "interfaces": interfaces, "routing": routing,
        "zone_wizard": zone_wizard, "search_grammar": search_grammar,
        "source_note": "Host/rule/zone data exported from test_sentrywall_core.estate() "
                        "— the exact fixture the 272-test suite runs against. "
                        "Firewall device names/interfaces are synthetic UI dressing.",
    }


if __name__ == "__main__":
    data = build()
    out = os.path.join(os.path.dirname(__file__), "data.json")
    with open(out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {out}  ({len(data['hosts'])} hosts, {len(data['rules'])} rules, "
          f"{len(data['objectgroups'])} groups)")
