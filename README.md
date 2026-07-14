<div align="center">
  <h1>SAO — Sira Agentic Orchestrator 🧠</h1>
  <p><b>The AI That Never Forgets — Permanent Memory Across Sessions</b></p>
</div>

---

**SAO** is not just another AI agent. It is a **personal AI operating system with permanent memory**. 

It wraps around **[Hermes Agent](https://hermes-agent.nousresearch.com/)** and treats your local Markdown vault as its brain. It remembers every conversation across sessions and never forgets — even when you open a new chat tab.

### Why SAO?

- **Never Forgets**  
  Every session (Desktop, CLI, Discord, Telegram) is automatically compiled into your vault. Cross-session memory is built-in, not bolted on. No context window limits your past — only your vault does.
- **Vault-Backed Memory**  
  Your vault (Obsidian or plain Markdown) is Sira's single source of truth. All conversations, decisions, and knowledge live there — searchable, linkable, permanent.
- **Hermes Core**  
  SAO uses **Hermes Agent** as its brain. You can chat via the official Hermes Desktop GUI, the CLI, or messaging gateways. SAO orchestrates the memory behind the scenes.
- **Self-Improving by Design**  
  SAO schedules background cron jobs (via Hermes) to run a structured daily digest and sync sessions every hour. Graphify continuously builds a knowledge graph from your entire vault.
- **Session-Agnostic**  
  Open a new session anytime — Sira will recall past context naturally. You never need to type a session ID, link old threads, or repeat yourself.
- **Worker is Optional**  
  By default, SAO uses Hermes itself (`sira`) for tasks. You can later plug Claude Code, OpenCode, or any CLI you prefer for coding tasks.
- **One Command Setup**  
  `sao install` handles everything: the official Hermes installer (including Desktop), Graphify, and the SAO memory skills.

---

## 🚀 Quick Start (Windows)

### 1. Prerequisites
- PowerShell / CMD
- **Node.js 20+**
- **Python 3.11+** ([python.org](https://www.python.org/downloads/) — check **"Add python.exe to PATH"**)

### 2. Install SAO & Hermes
This command installs the SAO CLI globally, then downloads the official Hermes Agent (including Desktop GUI) and Graphify.
```powershell
npm install -g git+https://github.com/gilangprtm/sao.git
sao install
```
*(If you already have Hermes installed, `sao install` will skip it and just install the SAO skills.)*

### 3. Create Your Vault
```powershell
sao create vault
```
*(We recommend opening this folder in **Obsidian** for the best human reading experience).*

### 4. Setup Model (First Run Only)
If you haven't set up Hermes before, pick your LLM provider and enter your API key:
```powershell
hermes setup
```

### 5. Launch Sira
```powershell
sao start
```
`sao start` will:
1. Bind Sira's memory to your Vault.
2. Register the SAO background memory sync (every 1 hour).
3. Update the Graphify Knowledge Graph.
4. Launch the **Hermes Desktop GUI** (or fallback to CLI chat).

You can now talk to Sira in the Hermes Desktop app. Your memory is permanent.

---

## 📋 CLI Commands

Run `sao -h` or `sao --help` to show usage help.

| Command | Description |
|---------|-------------|
| `sao install` | Install Hermes (if missing), Graphify, and SAO skills |
| `sao start` | Bind vault, update graph, register cron, launch Hermes (Desktop/CLI) |
| `sao start --clean-graph` | Full rebuild of the Graphify knowledge graph |
| `sao create vault` | Scaffold a new Sira vault (SIS, SOM-Lite, etc.) |
| `sao setup vault` | Link SAO to an existing Sira vault |
| `sao log` | Manually compile recent Hermes sessions into your vault |
| `sao log list` | List recent Hermes sessions and their vault status |
| `sao ingest` | Auto-format raw notes (`vault/raw/`) into clean wiki pages |
| `sao doctor` | Run health checks on SAO, Hermes, and the vault |

---

## 🧠 Memory Sync (Cron)

SAO registers background jobs in Hermes to sync your memory automatically:
- **Hourly**: Syncs new Hermes chat sessions into `vault/Sessions/`.
- **Daily (09:00)**: Syncs sessions and writes a daily journal + self-reflection in `vault/wiki/journal/`.

*Note: Background cron jobs require the Hermes Gateway or Desktop app to be running.*

## 🧑‍💻 Coding Workers (Optional)

Sira can delegate coding tasks to specialized CLIs. By default, Sira does the work itself.
```powershell
sao set worker claude       # Use Anthropic's Claude Code
sao set worker opencode     # Use OpenCode CLI
sao set worker codex        # Use OpenAI Codex
```

---
**Powered by:** [Hermes Agent](https://github.com/NousResearch/hermes-agent) + [Graphify](https://github.com/Graphify-Labs/graphify)
