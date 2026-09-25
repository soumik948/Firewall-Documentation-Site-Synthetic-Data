"""Merges core (generate_data.build()) + extended (generate_extended_data.build_extended())
into the final data.json. Core keys (hosts/rules/objectgroups/firewalls/interfaces/routing)
are untouched — still exactly test_sentrywall_core.estate2(), still what the 292 tests run
against. Extended keys (networks/big_hosts/big_groups/big_rules/big_firewalls/big_interfaces/
big_routing) are new, browsing-scale, additive."""
import json
import os

from generate_data import build as build_core
from generate_extended_data import build_extended

core = build_core()
ext = build_extended()

merged = dict(core)
merged.update(ext)
merged["networks"] = core.get("networks", []) + ext.get("networks", [])

# merge firewall category dicts (core has DC/OLD/Cloud; extended adds DMZ/AWS/Azure too)
merged_fw = {k: list(v) for k, v in core["firewalls"].items()}
for cat, devices in ext["big_firewalls"].items():
    merged_fw.setdefault(cat, [])
    merged_fw[cat] += devices
merged["firewalls_all"] = merged_fw   # core["firewalls"] stays untouched for anything relying on it

merged["source_note"] = (
    "Core (small, labelled 'core'): hosts/rules/zones exported from "
    "test_sentrywall_core.estate() — the exact fixture the 292-test suite runs against. "
    "Extended (large, labelled 'extended'): ~1,750 rules / ~1,750 hosts / 440 networks / "
    "52 firewalls across a 16-region synthetic telecom topology (WEB/APP/MW/DB/CNF/DMZ/MGMT/"
    "SVC/DR/CLOUD/EXT) — realism layer for browsing and search, generated separately, not run "
    "through the engine's pytest suite."
)

out = os.path.join(os.path.dirname(__file__), "data.json")
with open(out, "w") as f:
    json.dump(merged, f, indent=None, separators=(",", ":"))
sz = os.path.getsize(out)
print(f"wrote {out} ({sz/1024:.0f} KB) — "
      f"core: {len(core['hosts'])} hosts/{len(core['rules'])} rules/{len(core['objectgroups'])} groups | "
      f"extended: {len(ext['big_hosts'])} hosts/{len(ext['big_rules'])} rules/{len(ext['big_groups'])} groups/"
      f"{len(ext['networks'])} networks | firewalls total: {sum(len(v) for v in merged_fw.values())}")
