<div align="center">
  <h1>SAO — Sira Agentic Orchestrator 🧠</h1>
  <p><b>Your Personal, Self-Improving, Local-First AI Operating System</b></p>
</div>

---

**SAO** (Sira Agentic Orchestrator) is a local-first, multi-service personal AI operating system. It acts as the "engine" that powers your AI agent, while relying on a **Markdown vault folder** as its single source of truth and memory.

**Core:** Hermes (Brain) + 9Router (Gateway) + Graphify (Knowledge Graph)  
**Worker:** optional external coding CLI — or **Sira itself** by default.

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

## 📁 What `sao create vault` generates

```
Documents/<VaultName>/
├── AGENTS.md
├── SCHEMA.md
├── Philosophy/
│   ├── SIS.md             # Sira Intelligence System
│   └── SOM.md             # Sira Operating Manual
├── wiki/ + journal/
├── raw/
├── ingested/
├── graphify-out/
└── _templates/
```

## 📋 CLI Commands

| Command | Description |
|---------|-------------|
| `sao install` | Core only: Hermes + 9Router + Graphify (+ auto `uv`) |
| `sao create vault` | Generate Markdown vault |
| `sao setup vault` | Link existing vault |
| `sao set worker [cmd]` | Set coding worker (default `sira`) |
| `sao start` | Launch services |
| `sao status` | Services + vault + worker |
| `sao stop` | Stop services |

## FAQ

### Is Claude Code required?
**No.** Default worker is `sira`. Install Claude Code / OpenCode only if you want them.

### Is Obsidian required?
**No.** Vault is a folder of Markdown files.

### Linux / macOS / VPS?
Core design is local-first. Windows installer is ready; Linux/macOS scripts are planned. Manual service setup still works on Linux.

## 📜 License
MIT
