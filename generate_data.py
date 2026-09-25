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

    # Interfaces/zones per device — one illustrative device wired to real hosts (fwb-ahm1),
    # the rest lightly stubbed so every device page still renders something.
    interfaces = {
        "fwb-ahm1": [
            {"iface": "Mgmt", "subnet": "10.99.0.0/24", "zone": "MGMT",
             "description": "DCN-MGMT-01", "responsible": "n.schmidt@btnl-demo.local", "comment": "#100010"},
            {"iface": "bond1.410", "subnet": "10.50.1.0/24", "zone": "DMZ",
             "description": "DCN-DMZ-01", "responsible": "r.sharma@btnl-demo.local", "comment": "#100011"},
            {"iface": "bond1.797", "subnet": "10.20.1.0/24", "zone": "APP",
             "description": "DCN-APP-01", "responsible": "r.sharma@btnl-demo.local", "comment": "#100012"},
            {"iface": "bond1.780", "subnet": "10.30.1.0/24", "zone": "DB",
             "description": "DCN-DB-01", "responsible": "m.weber@btnl-demo.local", "comment": "#100013"},
        ],
    }

    routing = {
        "fwb-ahm1": [
            {"destination": "10.20.1.0/24", "gateway": "direct", "interface": "bond1.797"},
            {"destination": "10.30.1.0/24", "gateway": "direct", "interface": "bond1.780"},
            {"destination": "10.99.0.0/24", "gateway": "direct", "interface": "mgmt0"},
            {"destination": "0.0.0.0/0", "gateway": "10.50.1.1", "interface": "bond1.410"},
        ],
    }

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
