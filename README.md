<div align="center">
  <h1>SAO — Sira Agentic Orchestrator 🧠</h1>
  <p><b>The AI That Never Forgets — Permanent Memory Across Sessions</b></p>
</div>

---

**SAO** is not just another AI agent.

It is a **personal AI operating system with permanent memory**. It treats your Markdown vault as its brain, remembers every conversation across sessions, and never forgets — even when you open a new chat tab.

### Why SAO?

- **Never Forgets**  
  Every session (Discord, Telegram, CLI, TUI) is automatically compiled into your vault. Cross-session memory is built-in, not bolted on. No context window limits your past — only your vault does.

- **Vault-Backed Memory**  
  Your vault (Obsidian or plain Markdown) is the single source of truth. All conversations, decisions, and knowledge live there — searchable, linkable, permanent.

- **Self-Improving by Design**  
  Every day at 09:00, SAO writes a structured daily digest. Graphify continuously builds a knowledge graph from your entire vault.

- **Session-Agnostic**  
  Open a new session anytime — Sira will recall past context naturally. You never need to type a session ID, link old threads, or repeat yourself.

- **Worker is Optional**  
  By default, SAO uses itself (`sira`) as the coding worker. You can later plug Claude Code, OpenCode, or any CLI you prefer.

- **One Command, Zero Maintenance**  
  `sao install` handles everything: Hermes, Graphify, and `uv`.

- **Philosophy Built-In**  
  `sao create vault` generates a complete Sira-structured vault with full **SIS** (Sira Intelligence System), **SOM** (Sira Operating Manual), and a **`.graphignore`** filter to keep the graph lean.

- **Vault Cleaner**  
  `sao ingest` automatically transforms messy raw files under `vault/raw/` into clean wiki notes — no deep manual structuring needed.

---

**Powered by:** Hermes (Brain) + Graphify (Knowledge Graph)  
**Memory:** Your Vault (Markdown) + Sessions + Graph Index

---

## 🚀 Quick Start (Windows)

### 1. Prerequisites
- PowerShell / CMD
- **Node.js 20+**
- **Git**
- **Python 3.11+** ([python.org](https://www.python.org/downloads/) — check **"Add python.exe to PATH"**)

> **No need to install Hermes / uv / Graphify / Claude Code beforehand.**  
> `sao install` only installs the **core** (Hermes + Graphify + auto-`uv`).  
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
```powershell
sao set worker sira         # built-in (default)
sao set worker claude       # Claude Code CLI
sao set worker opencode     # OpenCode CLI
sao set worker <any-cmd>    # any binary on PATH
```

### 5. (Recommended) Open Vault in Obsidian
Vault = Markdown folder. Obsidian is optional for AI, recommended for humans.

### 6. Launch
```powershell
sao start                  # everyday (fast incremental graph update)
sao start --clean-graph    # after big deletes / stale graph nodes
```
- **Hermes**: brain + session store (`state.db`) + owns Graphify MCP (stdio)
- Graph index updated on `sao start`; query via Hermes MCP tools (no fixed Graphify HTTP port)

---

## 📋 CLI Usage & Commands

Run `sao -h` or `sao --help` to show usage help.

```
SAO - Sira Agentic Orchestrator

Usage:
  sao install                 # Install core: Hermes + Graphify (+ auto uv)
  sao create vault            # Generate Markdown vault with Sira structure
  sao setup vault             # Link existing vault folder
  sao set worker [cmd]        # Set coding worker (default: sira)
  sao start                   # Launch SAO (incremental graph update)
  sao start --clean-graph     # Launch + full graph rebuild (remove stale nodes)
  sao log                     # Sync all Hermes sessions → vault/Sessions/
  sao log list                # List sessions + vault status
  sao log session <id>        # Force recompile one growing session
  sao ingest                  # Ingest raw files from vault/raw/ into wiki/
  sao status                  # Check services + vault + worker
  sao doctor                  # Health check (vault, state.db, MCP, skills)
  sao doctor --smoke          # Health + isolated smoke tests
  sao stop                    # Stop all services
```

### Detail Commands

#### `sao install`
Clones core services (Hermes, Graphify), bootstraps envs via `uv`, installs deps. Does **not** install coding workers.

#### `sao create vault`
Interactively prompts for a vault name. Generates structure under `~/Documents/[VaultName]`:
```
Documents/<VaultName>/
├── AGENTS.md              # Sira instructions + memory continuity rules
├── SCHEMA.md              # Folder mappings and rules
├── Philosophy/
│   ├── SIS.md             # Sira Intelligence System (DNA)
│   └── SOM.md             # Sira Operating Manual (protocols)
├── wiki/
│   ├── index.md
│   └── journal/           # Daily digests (subconscious)
├── Sessions/              # Compiled Hermes session notes (auto-linked)
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
1. Bind vault path + write Hermes pointers (`sao_vault.json`, env `SAO_VAULT_PATH` / `HERMES_STATE_DB`)
2. Update Graphify index (incremental; use `--clean-graph` for full rebuild)
3. Register Graphify as **Hermes stdio MCP** (Hermes owns lifecycle — no separate port 20476)
4. Register subconscious cron if missing
5. Start Hermes Core (`20477`)

| Mode | When | Speed | Removes deleted-file nodes? |
|------|------|-------|-----------------------------|
| `sao start` | Everyday | Fast (incremental) | No — stale nodes can remain |
| `sao start --clean-graph` | After mass delete / graph feels wrong | Slower (1–3+ min large vault) | **Yes** — wipe `graphify-out` + reindex `--force` |

#### `sao log` / `sao log list` / `sao log session <id>`
Syncs Hermes conversation history into the vault:

| Command | Effect |
|---------|--------|
| `sao log` | Sync all sessions (create new + update if chat grows) |
| `sao log list` | List latest sessions + IN_VAULT / MISSING |
| `sao log session <id>` | Force recompile one long session |

Related sessions are **auto-linked** via token similarity — user never types session IDs.

#### `sao ingest`
Reads messy files (TXT, DOCX, XLSX, raw notes) inside `vault/raw/`. 
Sends them to Sira to compile into formatted Markdown notes under `vault/wiki/` (with YAML frontmatter and smart `[[wikilinks]]`), then archives the source file to `vault/ingested/` and runs a graph update.

#### `sao status`
Services (ACTIVE/INACTIVE), vault path, worker config, state.db path.

#### `sao doctor` / `sao doctor --smoke`
Health check: package files, vault structure, AGENTS inject, Hermes pointers, `state.db` schema, Graphify MCP registration, skills copy.

| Flag | Effect |
|------|--------|
| (none) | Health only |
| `--smoke` | + isolated temp vault (inject, pointer, session sync dry-run; **restores** your config) |
| `--strict` | WARN counts as failure (exit 1) |
| `--json` | CI-friendly JSON report |

Exit `0` if no FAIL. Use after install or when something feels off.

#### `sao stop`
Stop SAO-managed processes (Hermes on `20477`). Graphify has no separate SAO process when using stdio MCP.

---

## 🧠 How Memory Works

```
Hermes state.db (all platforms)  →  sao log  →  vault/Sessions/
                                                       │
                                                       ▼
                                              auto-link related sessions
                                               (Jaccard similarity)
                                                       │
                                                       ▼
                                              graphify update → graph index
                                                       │
                                                       ▼
                                              Sira recalls naturally
                                               (no user session IDs)
```

### Without SAO
```
Session 1: "set up auth"      → AI remembers
Session 2: "about the auth..." → AI forgets until you spoon-feed
Session 3: "auth question"    → AI has no idea
```

### With SAO
```
Session 1: "set up auth"      → vault/Sessions/session1.md
Session 2: "about the auth"   → Sira reads session1 → continues naturally
Session 3: "auth question"    → Sira reads session1+2 → knows the context
```

**The user never types a session ID. It just works.**

---

## 🛠️ Worker model

| Worker | How | Required? |
|--------|-----|-----------|
| **sira** (default) | Hermes handles coding tasks itself | No |
| **claude** | `claude` CLI on PATH | Optional |
| **opencode** | `opencode` CLI on PATH | Optional |
| **custom** | any CLI via `sao set worker` | Optional |

---

## FAQ

### Does SAO need a cloud account?
**No.** SAO runs on your machine. You choose your own LLM provider via Hermes config or your own custom gateway — no mandatory cloud account.

### Is Claude Code required?
**No.** Default worker is `sira`.

### Is Obsidian required?
**No.** Vault is a Markdown folder. Obsidian is recommended for humans.

### Will every `sao start` take 1 minute?
**No.** First index can be slow. Later starts use **incremental** update (seconds).

### Can SAO run on a VPS without screen?
Yes. All services run headless. CLI-only mode works on Linux VPS.

---

## 📜 License
MIT
