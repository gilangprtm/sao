<div align="center">
  <h1>SAO — Sira Agentic Orchestrator 🧠</h1>
  <p><b>Your Personal, Self-Improving, Local-First AI Operating System</b></p>
</div>

---

**SAO** (Sira Agentic Orchestrator) is a local-first, multi-service personal AI operating system. It acts as the "engine" that powers your AI agent, while relying on a **Markdown vault folder** as its single source of truth and memory.

Powered by: **Hermes** (The Brain) + **9Router** (Token-saving Gateway) + **Graphify** (Spatial Code Graph) + **Claude Code** (Autonomous Worker).

## 🚀 Quick Start (Windows)

### 1. Prerequisites
- PowerShell / CMD
- **Node.js 20+**
- **Git**
- **Python 3.11+** ([python.org](https://www.python.org/downloads/) — centang **"Add python.exe to PATH"**)

> **Tidak perlu install Hermes / uv / Graphify dulu.**  
> `sao install` otomatis: install `uv` (jika belum ada) → clone Hermes, 9Router, Graphify → setup env → install Claude Code.

### 2. Install SAO
Install the SAO CLI globally directly from GitHub (no NPM registry required):

```powershell
# Install SAO CLI globally from GitHub
npm install -g git+https://github.com/gilangprtm/sao.git

# One-shot installer (auto-installs uv + Hermes + 9Router + Graphify + Claude Code)
sao install
```

### 3. Create Your Vault
```powershell
sao create vault
```
*(You will be asked to name your Vault. SAO creates it under Documents and injects full DNA: `AGENTS.md`, `SCHEMA.md`, `Philosophy/SIS.md`, `Philosophy/SOM.md`, `wiki/`, `raw/`, `_templates/`.)*

> Already have a vault folder? Link it with `sao setup vault`.

### 4. (Recommended) Open Vault in Obsidian
**Vault = folder Markdown.** SAO only needs the folder path.  
**Obsidian is optional for AI**, but strongly recommended for humans (graph view, search, editing).

1. Download [Obsidian](https://obsidian.md/)
2. **Open folder as vault** → pilih folder yang dibuat `sao create vault`

Tanpa Obsidian, SAO tetap jalan. Catatan tetap bisa diedit di VS Code / Notepad / Cursor.

### 5. Launch
```powershell
sao start
```
- **9Router Dashboard**: http://localhost:20475
- **Hermes Gateway**: http://localhost:20477
- **Graphify MCP**: http://localhost:20476 (Indexing your Vault)

## 📁 What `sao create vault` generates

```
Documents/<VaultName>/
├── AGENTS.md              # Full agent rules (auto-read by Hermes)
├── SCHEMA.md              # Folder map + vault rules
├── Philosophy/
│   ├── SIS.md             # Full Sira Intelligence System (DNA)
│   └── SOM.md             # Full Sira Operating Manual (protocols)
├── wiki/
│   ├── index.md
│   └── journal/           # Daily digests from subconscious
├── raw/                   # Incoming unprocessed sources
├── ingested/              # Processed source archive
├── graphify-out/          # Graphify index output (graph.json)
└── _templates/
    └── note.md
```

> **HOM renamed to SOM** (Sira Operating Manual) — protocols belong to Sira, not Hermes branding.

## 📋 CLI Commands

| Command | Description |
|---------|-------------|
| `sao install` | Clone & install Hermes, 9Router, Graphify, Claude Code (+ auto-install `uv`) |
| `sao create vault` | Generate a new Markdown vault with Sira structure |
| `sao setup vault` | Link an existing vault folder (paste path) |
| `sao start` | Launch all SAO services |
| `sao status` | Check running services + vault path |
| `sao stop` | Stop all SAO services |

## 🧠 How SAO Learns (The Subconscious Loop)

SAO runs background tasks (Cron) without your input:
- **Daily Digest (09:00)**: Scans yesterday's tasks and writes a semantic summary into your vault (`wiki/journal/YYYY-MM-DD.md`).
- **Graph Sync**: Re-indexes your vault via `graphify --update`, so SAO understands relationships between notes and projects.

## FAQ

### Apakah vault wajib pakai Obsidian?
**Tidak.**  
Vault SAO = folder berisi Markdown + struktur `AGENTS.md` / `wiki/` / `Philosophy/`.  
- **SAO (AI)**: hanya butuh path folder → Graphify index → baca/tulis file.  
- **Obsidian**: editor manusia (recommended). Bisa diganti VS Code, Logseq, atau editor lain.

## 🤝 Contributing
SAO is designed to be extensible. To add a new sub-agent, ensure it runs as a local API and register it in the `scripts/start.ps1` orchestrator.

## 📜 License
MIT
