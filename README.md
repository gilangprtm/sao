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
sao start                  # everyday (fast incremental graph update)
sao start --clean-graph    # after big deletes / stale graph nodes
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
  sao install                 # Install core: Hermes + 9Router + Graphify (+ auto uv)
  sao create vault            # Generate Markdown vault with Sira structure
  sao setup vault             # Link existing vault folder
  sao set worker [cmd]        # Set coding worker (default: sira)
  sao start                   # Launch SAO (incremental graph update)
  sao start --clean-graph     # Launch + full graph rebuild (remove stale nodes)
  sao log                     # Sync Hermes sessions → vault/Sessions/
  sao status                  # Check services + vault + worker
  sao stop                    # Stop all services
```

### Detail Commands

#### `sao install`
Clones core services (Hermes, 9Router, Graphify), bootstraps envs via `uv`, installs deps. Does **not** install coding workers.

#### `sao create vault`
Interactively prompts for a vault name. Generates structure under `~/Documents/[VaultName]`:
```
Documents/<VaultName>/
├── AGENTS.md              # Sira instructions (auto-read by Hermes)
├── SCHEMA.md              # Folder mappings and rules
├── Philosophy/
│   ├── SIS.md             # Sira Intelligence System (DNA)
│   └── SOM.md             # Sira Operating Manual (protocols)
├── wiki/
│   ├── index.md
│   └── journal/           # Daily digests (subconscious)
├── Sessions/              # Compiled Hermes session notes (from sao log)
├── raw/                   # Unprocessed documents
├── ingested/              # Archive
├── graphify-out/          # Graph index output
└── _templates/
    └── note.md
```

#### `sao setup vault`
Link an existing vault folder. Writes path to `~/.sao/config.json`.

#### `sao set worker [sira|claude|opencode|<cmd>]`
Sets coding delegate. Default `sira`. Probes PATH and lists detected CLIs.

#### `sao start` / `sao start --clean-graph`
1. Start 9Router (`20475`)
2. Graphify index vault
3. Start Graphify MCP (`20476`)
4. Start Hermes (`20477`)

| Mode | When | Speed | Removes deleted-file nodes? |
|------|------|-------|-----------------------------|
| `sao start` | Everyday | Fast (incremental) | No — stale nodes can remain |
| `sao start --clean-graph` | After mass delete / graph feels wrong | Slower (1–3+ min large vault) | **Yes** — wipe `graphify-out` + reindex `--force` |

#### `sao log` / `sao log list` / `sao log session <id>`
Syncs Hermes conversation history into the vault:

```
Hermes state.db (Discord / Telegram / CLI / TUI)
        │
        ▼
  sao log  (manual)  OR  subconscious daily (09:00)
        │
        ▼
  vault/Sessions/<session_id>.md   ← update if chat grows
        │
        ▼
  wiki/journal/YYYY-MM-DD.md
```

| Command | Effect |
|---------|--------|
| `sao log` | Sync all sessions (create new + update if message_count naik) |
| `sao log list` | List latest sessions + IN_VAULT / MISSING |
| `sao log session <id>` | Force recompile one long-running session |

Each session note: ID, title, source, topics, first prompt, last resolution, wikilink slot.

#### `sao status`
Services (ACTIVE/INACTIVE), vault path, worker config, detected CLIs.

#### `sao stop`
Stop processes on ports `20475`–`20477`.

---

## 🕸️ Vault → Graph flow

```
Vault Markdown  →  graphify update  →  graphify-out/graph.json  →  MCP query  →  Sira
```

- **Source of truth**: vault files (never replaced by the graph)
- **Index**: `graphify-out/` (do not hand-edit)
- **Default start**: incremental (add/edit only; usually seconds)
- **After deletes**: `sao start --clean-graph` (stale nodes otherwise remain)

---

## 🧠 Session memory flow

```
Chat (Discord/Telegram/CLI)  →  Hermes state.db  →  sao log  →  Sessions/*.md  →  Graphify
```

Sira does **not** dump raw chat into the vault. It compiles:
- session ID
- what was discussed (title + first prompt + last resolution)
- links for follow-up in `wiki/`

Run manually anytime:
```powershell
sao log
```

Or let daily subconscious (`subconscious.py daily`) do sync + journal together.

---

## 🛠️ Worker model

| Worker | How | Required? |
|--------|-----|-----------|
| **sira** (default) | Hermes handles coding tasks itself | No |
| **claude** | `claude` CLI on PATH | Optional |
| **opencode** | `opencode` CLI on PATH | Optional |
| **custom** | any CLI via `sao set worker` | Optional |

Config `~/.sao/config.json`:
```json
{
  "vault_path": "C:\\Users\\you\\Documents\\MyVault",
  "worker": "sira",
  "worker_cmd": ""
}
```

## FAQ

### Is Claude Code required?
**No.** Default worker is `sira`.

### Is Obsidian required?
**No.** Vault is a Markdown folder. Obsidian is recommended for humans.

### Will every `sao start` take 1 minute?
**No.** First index can be slow. Later starts use **incremental** update (seconds if little changed). Use `--clean-graph` only when you need a full rebuild.

### Linux / macOS / VPS?
Windows installer ready. Linux/macOS scripts planned. Manual service setup works on Linux.

## 📜 License
MIT
