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

### 2. Install Obsidian & Create a Vault
SAO needs a brain. We use Obsidian for this.
1. Download and install [Obsidian](https://obsidian.md/).
2. Create a new Vault (you can name it `Sira-Vault` or anything you like).
3. Note down the folder path of your new Vault (e.g., `C:\Users\YourName\Documents\MyVault`).

### 3. Install SAO
SAO provides a convenient NPM wrapper for global access.

```powershell
# Install the SAO CLI globally
npm install -g sira-agentic-orchestrator

# Run the SAO installer (clones services, sets up environments)
sao install
```

### 4. Connect SAO to Your Vault
Tell SAO where your brain is located:

```powershell
sao setup vault
```
*(When prompted, paste the folder path from Step 2)*

### 5. Launch
Start the entire SAO homelab with one command:

```powershell
sao start
```
- **9Router Dashboard**: http://localhost:20128
- **Hermes Gateway**: http://localhost:8080
- **Graphify MCP**: http://localhost:5001 (Indexing your Vault)

## 🧠 How SAO Learns (The Subconscious Loop)

SAO runs background tasks (Cron) without your input:
- **Daily Digest (09:00)**: Scans yesterday's tasks and writes a semantic summary directly into your Vault (`wiki/journal/YYYY-MM-DD.md`).
- **Graph Sync**: Re-indexes your Vault via `graphify --update` automatically, ensuring SAO always understands the relationships between your notes and projects.

## 🤝 Contributing
SAO is designed to be extensible. To add a new sub-agent, ensure it runs as a local API and register it in the `scripts/start.ps1` orchestrator.

## 📜 License
MIT
