<div align="center">
  <h1>SAO — Sira Agentic Orchestrator 🧠</h1>
  <p><b>Your Personal, Self-Improving, Local-First AI Operating System</b></p>
</div>

---

**SAO** is not just another AI agent.

It is a **complete personal AI operating system** that runs 100% on your machine, uses your Obsidian vault as its permanent brain, and improves itself over time — without sending your data anywhere.

### Why SAO?

- **True Local-First**  
  Everything (Hermes, 9Router, Graphify, memory) runs locally. No cloud, no telemetry, no API keys exposed.

- **Your Vault is the Brain**  
  SAO treats your Obsidian vault as the single source of truth. It reads, writes, and indexes your notes continuously.

- **Self-Improving by Design**  
  Every day at 09:00, SAO writes a structured daily digest into your vault. Graphify continuously builds a knowledge graph of your entire vault.

- **Worker is Optional**  
  By default, SAO uses itself (`sira`) as the coding worker. You can later plug Claude Code, OpenCode, or any CLI you prefer. No lock-in.

- **One Command, Zero Maintenance**  
  `sao install` handles everything: Hermes, 9Router, Graphify, and `uv`. No manual setup required.

- **Philosophy Built-In**  
  `sao create vault` generates a complete Sira-structured vault with full **SIS** (Sira Intelligence System) and **SOM** (Sira Operating Manual) — not empty placeholders.

---

**Powered by:** Hermes (Brain) + 9Router (Gateway) + Graphify (Knowledge Graph)

---

## 🚀 Quick Start (Windows)

### 1. Prerequisites
- PowerShell / CMD
- **Node.js 20+**
- **Git**
- **Python 3.11+** ([python.org](https://www.python.org/downloads/) — check **"Add python.exe to PATH"**)

> **No need to install Hermes / uv / Graphify / Claude Code beforehand.**  
> `sao install` only installs the **core** (Hermes + 9Router + Graphify + auto-`uv`).  
> Coding workers are **optional**.

### 2. Install SAO
```powershell
npm install -g git+https://github.com/gilangprtm/sao.git
sao install
```

### 3. Create Your Vault
```powershell
sao create vault
```

### 4. (Optional) Set a coding worker
By default the worker is **`sira`** (Hermes itself handles coding).

```powershell
sao set worker              # show current + detected CLIs
sao set worker sira         # built-in (default)
sao set worker claude       # Claude Code CLI (if installed)
sao set worker opencode     # OpenCode CLI
sao set worker <any-cmd>    # any binary on PATH
```

SAO **never** auto-installs Claude Code / OpenCode. Install those yourself if you want them.

### 5. (Recommended) Open Vault in Obsidian
Vault = Markdown folder. Obsidian is optional for AI, recommended for humans.

### 6. Launch
```powershell
sao start
```
- **9Router**: http://localhost:20475
- **Graphify MCP**: http://localhost:20476
- **Hermes**: http://localhost:20477

---

## 📋 CLI Usage & Commands

Run `sao -h` or `sao --help` to show usage help.

```
SAO - Sira Agentic Orchestrator

Usage:
  sao install            # Install core: Hermes + 9Router + Graphify (+ auto uv)
  sao create vault       # Generate Markdown vault with Sira structure
  sao setup vault        # Link existing vault folder
  sao set worker [cmd]   # Set coding worker (default: sira)
  sao start              # Launch SAO services
  sao status             # Check services + vault + worker
  sao stop               # Stop all services
```

### Detail Commands

#### `sao install`
Clones repository services (Hermes, 9Router, Graphify) into globally installed SAO module directory, bootstraps virtual environments via `uv`, installs package dependencies, and links executable PATH.

#### `sao create vault`
Interactively prompts for a new Vault folder name. Generates structure under `~/Documents/[VaultName]`:
```
Documents/<VaultName>/
├── AGENTS.md              # Sira instructions (auto-read by Hermes)
├── SCHEMA.md              # Folder mappings and rules
├── Philosophy/
│   ├── SIS.md             # Sira Intelligence System (DNA)
│   └── SOM.md             # Sira Operating Manual (protocols)
├── wiki/
│   ├── index.md
│   └── journal/           # Daily digests written by SAO subconscious
├── raw/                   # Unprocessed documents
├── ingested/              # Archive directory
├── graphify-out/          # Index folder for Graphify MCP
└── _templates/
    └── note.md
```

#### `sao setup vault`
Lets you link an existing vault folder if you do not want to use `sao create vault`. Writes path to `~/.sao/config.json`.

#### `sao set worker [sira|claude|opencode|<cmd>]`
Sets Sira's coding delegate command. Default is `sira`. Probes local environment and lists detected executors. Saves configuration to `~/.sao/config.json`.

#### `sao start`
Starts the local orchestrator:
1. Runs 9Router (Port `20475`)
2. Reads config and launches Graphify MCP indexing the target vault (Port `20476`)
3. Starts Hermes Core (Port `20477`) with configuration injected.

#### `sao status`
Inspects network ports and reports service statuses (ACTIVE/INACTIVE), currently configured vault path, and selected coding worker.

#### `sao stop`
Kills running SAO service processes listening on ports `20475` to `20477` gracefully or via force taskkill fallback.

---

## 🛠️ Worker model

| Worker | How | Required? |
|--------|-----|-----------|
| **sira** (default) | Hermes handles coding tasks itself | No |
| **claude** | `claude` CLI on PATH | Optional |
| **opencode** | `opencode` CLI on PATH | Optional |
| **custom** | any CLI you pass to `sao set worker` | Optional |

Config stored in `~/.sao/config.json`:
```json
{
  "vault_path": "C:\\Users\\you\\Documents\\MyVault",
  "worker": "sira",
  "worker_cmd": ""
}
```

## FAQ

### Apakah vault wajib pakai Obsidian?
**Tidak.**  
Vault SAO = folder berisi Markdown + struktur `AGENTS.md` / `wiki/` / `Philosophy/`.  
- **SAO (AI)**: hanya butuh path folder → Graphify index → baca/tulis file.  
- **Obsidian**: editor manusia (recommended). Bisa diganti VS Code, Logseq, atau editor lain.

### Linux / macOS / VPS?
Core design is local-first. Windows installer is ready; Linux/macOS scripts are planned. Manual service setup still works on Linux.

## 📜 License
MIT
