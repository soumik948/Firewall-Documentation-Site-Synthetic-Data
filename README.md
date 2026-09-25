# Firewall Documentation System — Synthetic Demo Site

A look-alike clone of the internal Firewall Documentation System (per the 18 provided screenshots),
rebuilt with 100% synthetic data. Static HTML/CSS/vanilla JS, no backend, no build step, ₹0 to host.

## Two-site architecture — read this first

This site and the actual verification agent are **two separate deployments, two separate URLs**:

```
  Documentation site (this repo)          FRVA — FW Rule Verification Agent (separate app)
  ─────────────────────────────           ────────────────────────────────────────────────
  Existing FW rules only, read-only  <───  reads this site as its temporary-RAG source
  NEVER accepts an upload                  fw_template.xlsx is uploaded HERE, not on the doc site
                                            Button ① template/fill-up check
                                            chat section (clarifier Q&A)
                                            Button ② full rule-change verification
                                            🟢/🟠/🔴/⚪ flag + findings + downloadable report
```

This repo builds **only the left-hand side**. Nothing in here parses an uploaded workbook or renders
a flag — that logic lives in the agent codebase (`../agent/`) and its own frontend, deployed as FRVA
at a different URL. Keeping them apart matters for two reasons: (1) a static, no-auth doc site must
never be the place a real change request or its verdict lands, and (2) FRVA's masking/audit boundary
(see `FW_Agent_Platform_Design_v2.md` §14) only makes sense if the request/verdict path is a single,
audited system — not split across a public-looking static site too.

## What's real vs synthetic

- **Core dataset** (`hosts` / `rules` / `objectgroups`, plus the `tier:"core"` entries in
  `networks`) is exported directly from `test_sentrywall_core.estate()` — the exact fixture
  FRVA's 292-test suite runs against. Small (17 hosts / 9 rules), on purpose: the engine needs
  targeted scenarios, not volume.
- **Extended dataset** (`big_hosts` / `big_rules` / `big_groups` / `big_firewalls` /
  `big_interfaces` / `big_routing`, plus `tier:"extended"` entries in `networks`) is a separate,
  much larger synthetic layer — ~1,750 rules, ~1,750 hosts, 440 networks across 16 regions
  (WEB/APP/MW/DB/CNF/DMZ/MGMT/SVC/DR/CLOUD/EXT), 63 firewalls — built to *look and feel* like a
  real large telecom estate for browsing and RAG lookup. **Not** run through the pytest suite —
  that's deliberate, not an oversight (see the docstring in `generate_extended_data.py`).
  Regenerate both with `python3 merge_and_write.py`.
- **Firewall device inventory, interfaces, routing tables** are synthetic `btnl-demo` naming —
  every device (core and extended) now has interfaces and routes, not just one illustrative one.
- **Logo** (`logo.svg`) is an original placeholder mark, not the real BTNL logo (which is a live
  trademark) — same spirit as the synthetic `@btnl-demo.local` identities already used by
  `synthetic_ldap.py`.

## Search — how the IP lookup actually works now

A bare IPv4 address gets the full real-portal-style lookup (`common.js`):
1. Find every `networks` entry whose CIDR contains the IP, most-specific first — this is real
   CIDR math (`cidrContainsIp`), not a substring match, so **an IP with no exact host record
   still resolves correctly** to its containing subnet and the broader regions above it
   ("Bigger networks"), exactly like the real portal. This was the reported bug; it's fixed and
   covered by a Node-level regression check against the real merged dataset.
2. Group membership resolves recursively through `tokenMatchesIp()` (handles literal IP, CIDR
   member, or nested group token).
3. Routes scans both `routing` and `big_routing` for any destination CIDR containing the IP.
4. **New:** "Accessrules for `<ip>` to other systems" / "from other systems" — scans every rule
   (core + extended) and resolves every source/destination token (literal IP, CIDR, or group) to
   see if it covers the searched IP, matching the two-table report style in the source screenshots.

Anything that isn't a bare IPv4 still uses the original query grammar (`src:`/`dst:`/`serv:`/
`action:`/`fw:`, `and`/`or`/`!`, parens) — unchanged.

## Pages

| File | Mirrors screenshot(s) |
|---|---|
| `login.html` | Image 1 — cosmetic only, no real auth |
| `index.html` | Image 2's nav bar — Home |
| `firewalls.html` | Image 2 — grouped device list, now DC / DMZ / Cloud / AWS / Azure / OLD (63 devices) |
| `firewall-detail.html?id=<fw>&tab=<iface\|groups\|routing\|rules>` | Images 3–5, 14–16 — Access Rules now filtered to that specific firewall |
| `zone-app.html` | Images 6–10 — Yes/No classification wizard |
| `search.html` | Images 1–4, 11–16 — full IP lookup + query grammar |
| `request-checker.html` | Points to FRVA (separate app/URL) — no upload happens on this site |

## Preview locally

```
python3 -m http.server 8000
# open http://127.0.0.1:8000/login.html
```
(any static server works — this is plain files, nothing to install beyond Python or Node.)

## Regenerate the dataset

```
cd site/   # ../agent/ must sit next to this folder so test_sentrywall_core.py is importable
python3 merge_and_write.py   # runs generate_data.py (core) + generate_extended_data.py (extended)
```

## Host free on GitHub Pages

1. Create a new **public** GitHub repo, e.g. `sentrywall-demo-site`.
2. Push just this `site/` folder's contents to the repo root (keep `.nojekyll`).
3. Repo → **Settings → Pages** → Source: `Deploy from a branch` → Branch: `main` / `(root)` → Save.
4. GitHub gives you a URL like `https://<user>.github.io/sentrywall-demo-site/login.html` within a
   minute or two — ₹0, no expiry, fully decoupled from any Azure spend or the real product's auth.

Alternative: same steps against an Azure Static Web App (Free tier) if you'd rather keep everything
in one Azure resource group — either works; GitHub Pages is the simpler of the two for a
demo-only, no-auth site like this one.
