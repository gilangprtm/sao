# Roadmap: SAO Phase 6+ (Vault Integration & Hardening)

Berfokus menyatukan SAO sebagai mesin murni dengan **vault user** (path dari `~/.sao/config.json`) sebagai otak tunggal (Single Source of Truth).

---

## ✅ Done (shipped)

- Subconscious daily → `wiki/journal/` + `Sessions/` (no ledger DB)
- Graphify MCP on start → **stdio under Hermes** (`mcp_servers.graphify`), vault path from config
- `state.db` resolved dynamically (env / config / profile scan) for subconscious
- Env harden: `SAO_VAULT_PATH`, `HERMES_STATE_DB`
- `.graphignore` + `sao ingest` for clean graph at scale
- Gateway-agnostic (no mandatory 9Router)
- HOM → SOM; CEO dashboard refs removed from default DNA

---

## 🧠 Phase 6: Deep Vault Integration (remaining)

1. **Graphify native Hermes tool**
   - Optional direct tool wrapping MCP `localhost:20476`
   - Always resolve vault via `~/.sao/config.json` → `vault_path`
2. **Auto-Update Index**
   - File watcher / post-ingest hook (partially done via `sao ingest` + `sao start`)

## 🚀 Phase 7: Subsystem Hardening

1. **Service Manager (PM2 / Systemd / Docker)**
   - Auto-restart Graphify + Hermes
2. **Upstream Sync Mechanism**
   - Pull Hermes/Graphify upstream without breaking SAO patches

## 🛠️ Phase 8: Worker Independence

1. Worker abstraction (already: `sao set worker`)
2. Stronger OpenCode/Claude/Codex docs
3. Optional multi-agent registry

## 🌐 Phase 9: UI (optional)

1. Local control panel for service status + graph viz
2. **Not** required for SAO core identity (permanent memory)

---

## Hard rules for contributors

- **Never hardcode** `C:\Users\<name>\Documents\...` vault paths in skills, templates, or scripts.
- Vault path = `~/.sao/config.json` only.
- Core services = Hermes + Graphify only.
