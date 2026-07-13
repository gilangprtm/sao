<div align="center">
  <h1>SAO — Sira Agentic Orchestrator 🧠</h1>
  <p><b>Your Personal, Self-Improving, Local-First AI Operating System</b></p>
</div>

---

**SAO** (Sira Agentic Orchestrator) is a local-first, multi-service personal AI operating system. It acts as the "engine" that powers your AI agent, while relying on an **Obsidian Vault** as its single source of truth and memory.

Powered by: **Hermes** (The Brain) + **9Router** (Token-saving Gateway) + **Graphify** (Spatial Code Graph) + **Claude Code** (Autonomous Worker).

## 🚀 Quick Start (Windows)

### 1. Prerequisites
- Git Bash / PowerShell
- Python 3.11+ & `uv`
- Node.js 20+
- Git

### 2. Download Obsidian
SAO needs a brain to store its knowledge, philosophy, and memory. We use Obsidian for this.
1. Download and install [Obsidian](https://obsidian.md/).
2. You don't need to create the Vault yet — SAO will generate the correct structure for you in the next steps.

### 3. Install SAO
Install the SAO CLI globally directly from GitHub (no NPM registry required):

```powershell
# Install SAO CLI globally from GitHub
npm install -g git+https://github.com/gilangprtm/sao.git

# Run the SAO installer (clones Hermes, 9Router, Graphify + sets up environments)
sao install
```

### 4. Create & Connect Your Sira-Vault
Tell SAO to generate your brain structure:

```powershell
sao create vault
```
*(You will be asked to name your Vault. SAO will create it in your Documents folder and inject the necessary DNA like `AGENTS.md` and `Philosophy/` folder).*

> **Note**: If you already have an existing Sira-Vault, you can link it manually using `sao setup vault`.

### 5. Launch
Start the entire SAO homelab with one command:

```powershell
sao start
```
- **9Router Dashboard**: http://localhost:20128
- **Hermes Gateway**: http://localhost:8080
- **Graphify MCP**: http://localhost:5001 (Indexing your Vault)

## 📋 CLI Commands

| Command | Description |
|---------|-------------|
| `sao install` | Clone & install Hermes, 9Router, Graphify, Claude Code |
| `sao create vault` | Generate a new Obsidian Vault with Sira structure |
| `sao setup vault` | Link an existing Vault (paste path) |
| `sao start` | Launch all SAO services |
| `sao status` | Check running services + vault path |
| `sao stop` | Stop all SAO services |

## 🧠 How SAO Learns (The Subconscious Loop)

SAO runs background tasks (Cron) without your input:
- **Daily Digest (09:00)**: Scans yesterday's tasks and writes a semantic summary directly into your Vault (`wiki/journal/YYYY-MM-DD.md`).
- **Graph Sync**: Re-indexes your Vault via `graphify --update` automatically, ensuring SAO always understands the relationships between your notes and projects.

## 🤝 Contributing
SAO is designed to be extensible. To add a new sub-agent, ensure it runs as a local API and register it in the `scripts/start.ps1` orchestrator.

## 📜 License
MIT
