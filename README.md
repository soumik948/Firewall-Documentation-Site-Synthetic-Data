# Firewall Documentation System — Synthetic Demo Site

A look-alike clone of the internal Firewall Documentation System (per the 18 provided screenshots),
rebuilt with 100% synthetic data. Static HTML/CSS/vanilla JS, no backend, no build step, ₹0 to host.

## What's real vs synthetic

- **Host/zone/rule data** (`data.json`'s `hosts` / `rules` / `objectgroups`) is exported directly
  from `test_sentrywall_core.estate()` — the exact fixture the Sentrywall agent's 272-test suite
  runs against. Re-run `python3 generate_data.py` any time the agent's fixtures change to keep the
  clone in sync — this is why it's a *snapshot that regenerates on demand*, matching how the real
  portal "only updates when FW rules update."
- **Firewall device inventory, interfaces, routing tables** are UI dressing — hand-authored,
  synthetic `btnl-demo` naming, not derived from any real system.
- **Logo** (`logo.svg`) is an original placeholder mark, not the real BTNL logo (which is a live
  trademark) — same spirit as the synthetic `@btnl-demo.local` identities already used by
  `synthetic_ldap.py`.

## Pages

| File | Mirrors screenshot(s) |
|---|---|
| `login.html` | Image 1 — cosmetic only, no real auth |
| `index.html` | Image 2's nav bar — Home |
| `firewalls.html` | Image 2 — grouped device list (DC / OLD / Cloud) |
| `firewall-detail.html?id=<fw>&tab=<iface\|groups\|routing\|rules>` | Images 3–5, 14–16 |
| `zone-app.html` | Images 6–10 — Yes/No classification wizard |
| `search.html` | Images 11–13 — query grammar (`src:`/`dst:`/`serv:`/`action:`/`fw:`, `and`/`or`/`!`/parens) |
| `request-checker.html` | Points to the actual Sentrywall agent app |

## Preview locally

```
python3 -m http.server 8000
# open http://127.0.0.1:8000/login.html
```
(any static server works — this is plain files, nothing to install beyond Python or Node.)

## Regenerate the dataset

```
cd ../  # so ../agent/test_sentrywall_core.py is importable
python3 site/generate_data.py
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
