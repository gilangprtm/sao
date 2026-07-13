#!/usr/bin/env python3
"""
SAO CLI — Sira Agentic Orchestrator
Commands: install-related helpers, start/status/stop, create/setup vault, set worker, log sessions
"""

import argparse
import subprocess
import sys
import os
import shutil
import socket
import json
import shutil as sh

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
START_SCRIPT = os.path.join(BASE_DIR, "scripts", "start.ps1")
CONFIG_PATH = os.path.expanduser("~/.sao/config.json")

SERVICES = {
    "Graphify MCP": 20476,
    "Hermes Core": 20477
}

# Known coding worker CLIs (optional — SAO never requires them)
KNOWN_WORKERS = [
    ("claude", "Claude Code"),
    ("opencode", "OpenCode"),
    ("codex", "OpenAI Codex CLI"),
    ("aider", "Aider"),
    ("cursor", "Cursor Agent CLI"),
]


def get_psutil():
    try:
        import psutil
        return psutil
    except ImportError:
        print("Installing required module 'psutil'...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
        return psutil


def default_config():
    return {
        "vault_path": "",
        "worker": "sira",
        "worker_cmd": "",
    }


def load_config():
    cfg = default_config()
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        return cfg
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg.update(data or {})
        return cfg
    except Exception:
        return cfg


def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def command_exists(cmd):
    return sh.which(cmd) is not None


def detect_workers():
    found = []
    for cmd, label in KNOWN_WORKERS:
        if command_exists(cmd):
            found.append({"cmd": cmd, "label": label, "path": sh.which(cmd)})
    return found


def resolve_worker(config=None):
    """Return (name, cmd) for active worker."""
    config = config or load_config()
    name = (config.get("worker") or "sira").strip().lower()
    cmd = (config.get("worker_cmd") or "").strip()

    if name == "sira" or name == "hermes" or name == "self":
        return ("sira", None)

    if cmd:
        return (name, cmd)

    # name itself may be a CLI binary
    if command_exists(name):
        return (name, name)

    return (name, None)


def cmd_create_vault():
    print("🧠 SAO Create Vault\n")
    print("This will create a new Markdown vault with Sira structure (AGENTS.md, wiki/, Philosophy/SIS+SOM, etc.).\n")

    name = input("Enter the name for your new Vault (e.g., Sira-Vault): ").strip()
    if not name:
        print("❌ Vault name cannot be empty.")
        return

    base_path = os.path.expanduser("~/Documents")
    vault_path = os.path.join(base_path, name)

    if os.path.exists(vault_path):
        print(f"❌ Error: Folder '{vault_path}' already exists.")
        return

    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(pkg_dir, "templates", "vault")

    try:
        if os.path.isdir(template_dir):
            for root, dirs, files in os.walk(template_dir):
                rel = os.path.relpath(root, template_dir)
                dest_dir = os.path.join(vault_path, rel) if rel != "." else vault_path
                os.makedirs(dest_dir, exist_ok=True)
                for f in files:
                    src = os.path.join(root, f)
                    dst = os.path.join(dest_dir, f)
                    shutil.copy2(src, dst)
        else:
            with open(os.path.join(vault_path, "AGENTS.md"), "w", encoding="utf-8") as f:
                f.write("# Agent Instructions\n\n> Placeholder. Full template not found.\n")
            os.makedirs(os.path.join(vault_path, "Philosophy"), exist_ok=True)
            with open(os.path.join(vault_path, "Philosophy", "SIS.md"), "w", encoding="utf-8") as f:
                f.write("# Sira Intelligence System (SIS)\n\n> DNA operasional Sira.\n")
            with open(os.path.join(vault_path, "Philosophy", "SOM.md"), "w", encoding="utf-8") as f:
                f.write("# Sira Operating Manual (SOM)\n\n> Protokol operasional Sira.\n")

        required_dirs = [
            "wiki/journal",
            "Philosophy",
            "raw",
            "ingested",
            "graphify-out",
            "_templates",
            "Sessions",
        ]
        for d in required_dirs:
            dir_path = os.path.join(vault_path, d)
            os.makedirs(dir_path, exist_ok=True)
            if d in ("raw", "ingested", "graphify-out", "wiki/journal"):
                gitkeep = os.path.join(dir_path, ".gitkeep")
                if not os.path.exists(gitkeep):
                    open(gitkeep, "a", encoding="utf-8").close()

        config = load_config()
        config["vault_path"] = vault_path
        save_config(config)

        print(f"\n✅ Vault '{name}' created successfully at:\n   {vault_path}")
        print("✅ Structure: AGENTS.md, SCHEMA.md, Philosophy/SIS+SOM, wiki/, raw/, ingested/, graphify-out/, _templates/, Sessions/")
        print("✅ Full SIS + SOM content included (not placeholders).")
        print("✅ Path saved to config. Next: open folder in Obsidian (optional), then 'sao start'.")

    except Exception as e:
        print(f"❌ Failed to create vault: {e}")


def cmd_setup_vault():
    print("🔧 SAO Vault Setup\n")
    print("SAO requires a Markdown vault folder as its brain/memory.\n")

    config = load_config()
    current_vault = config.get("vault_path", "")

    if current_vault:
        print(f"Current Vault Path: {current_vault}")
        change = input("Do you want to change this path? [y/N]: ").strip().lower()
        if change != "y":
            print("Setup cancelled.")
            return

    while True:
        path = input("Enter the full path to your Vault:\n> ").strip()

        if not path:
            print("\n⚠️ Setup cancelled.")
            break

        path = path.strip("\"'")

        if os.path.isdir(path):
            config["vault_path"] = path
            save_config(config)
            print(f"\n✅ Vault path successfully saved: {path}")
            break
        else:
            print("\n❌ Error: That directory does not exist. Please enter a valid path.")


def cmd_set_worker(worker_cmd=None):
    """
    sao set worker              → interactive / show current
    sao set worker sira         → use Hermes itself
    sao set worker claude       → use CLI named 'claude'
    sao set worker opencode     → use OpenCode
    """
    config = load_config()
    found = detect_workers()

    print("🛠️  SAO Worker Configuration\n")
    print("Worker = coding executor Sira can call via terminal.")
    print("Default: sira (Hermes itself — no external CLI required).\n")

    wname, wcmd = resolve_worker(config)
    print(f"Current: worker={wname}" + (f"  cmd={wcmd}" if wcmd else "  (built-in)"))
    if found:
        print("Detected on PATH:")
        for w in found:
            print(f"  - {w['cmd']}  ({w['label']})  → {w['path']}")
    else:
        print("Detected on PATH: (none)")

    if not worker_cmd:
        print("\nUsage:")
        print("  sao set worker sira        # Hermes itself (default)")
        print("  sao set worker claude      # Claude Code CLI")
        print("  sao set worker opencode    # OpenCode CLI")
        print("  sao set worker <any-cmd>   # any binary on PATH")
        return

    worker_cmd = worker_cmd.strip()
    lower = worker_cmd.lower()

    if lower in ("sira", "hermes", "self", "none", "default"):
        config["worker"] = "sira"
        config["worker_cmd"] = ""
        save_config(config)
        print("\n✅ Worker set to: sira (Hermes built-in)")
        print("   External coding CLI not required.")
        return

    # Treat argument as CLI binary name
    if not command_exists(worker_cmd):
        print(f"\n⚠️  Warning: '{worker_cmd}' not found on PATH right now.")
        print("   Saving anyway — install the CLI later and restart terminal.")
        confirm = input("Continue? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return

    config["worker"] = lower
    config["worker_cmd"] = worker_cmd
    save_config(config)
    print(f"\n✅ Worker set to: {lower}")
    print(f"   CLI command: {worker_cmd}")
    print("   Sira will invoke this via terminal when delegating coding tasks.")


def cmd_start(clean_graph=False):
    config = load_config()
    if not config.get("vault_path"):
        print("❌ Error: Vault path is not set.")
        print("Please run 'sao create vault' or 'sao setup vault' first.")
        sys.exit(1)

    wname, wcmd = resolve_worker(config)
    print("🚀 Starting SAO (Sira Agentic Orchestrator)...")
    print(f"   Worker: {wname}" + (f" ({wcmd})" if wcmd else " [built-in]"))
    if clean_graph:
        print("   Graph: CLEAN rebuild (wipe stale nodes + full reindex)")
    else:
        print("   Graph: incremental update (use --clean-graph after big deletes)")

    ps_args = [
        "powershell.exe",
        "-ExecutionPolicy", "Bypass",
        "-File", START_SCRIPT,
    ]
    if clean_graph:
        ps_args.append("-CleanGraph")

    subprocess.run(ps_args)


def cmd_status():
    print("📊 SAO Services Status:")
    all_ok = True
    for name, port in SERVICES.items():
        active = is_port_in_use(port)
        status_str = "ACTIVE" if active else "INACTIVE"
        color = "\033[92m" if active else "\033[91m"
        print(f"  - {name} (Port {port}): {color}{status_str}\033[0m")
        if not active:
            all_ok = False

    config = load_config()
    vault = config.get("vault_path")
    if vault:
        print(f"\n📂 Target Vault: {vault}")
    else:
        print("\n📂 Target Vault: NOT CONFIGURED (Run 'sao create vault' or 'sao setup vault')")

    wname, wcmd = resolve_worker(config)
    print(f"🛠️  Worker: {wname}" + (f"  cmd=`{wcmd}`" if wcmd else "  [built-in Hermes/Sira]"))
    found = detect_workers()
    if found:
        print("   Available CLIs: " + ", ".join(w["cmd"] for w in found))
    else:
        print("   Available CLIs: (none detected)")

    if all_ok:
        print("\n🟢 All services are running properly.")
    else:
        print("\n🔴 Some services are offline. Run 'sao start' to launch them.")


def cmd_stop():
    print("🛑 Stopping SAO services...")
    stopped_any = False

    psutil = get_psutil()
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            connections = proc.connections()
            for conn in connections:
                if conn.laddr.port in SERVICES.values():
                    print(f"  - Killing {proc.info['name']} (PID: {proc.info['pid']}) on Port {conn.laddr.port}...")
                    proc.kill()
                    stopped_any = True
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    for port in SERVICES.values():
        try:
            output = subprocess.check_output(f"netstat -ano | grep :{port}", shell=True).decode()
            for line in output.strip().split("\n"):
                parts = line.split()
                if len(parts) > 4:
                    pid = parts[-1]
                    print(f"  - Force taskkill PID {pid} on port {port}...")
                    subprocess.run(["taskkill", "/F", "/PID", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    stopped_any = True
        except subprocess.CalledProcessError:
            continue

    if stopped_any:
        print("\n🟢 All SAO services stopped successfully.")
    else:
        print("\n⚪ No running SAO services detected.")


def cmd_log_sessions(session_id=None, list_only=False):
    """sao log | sao log list | sao log session <id>

    - list: show Hermes sessions + vault note status
    - session <id>: force recompile one growing session
    - (default): sync all sessions (create new + update longer ones)
    """
    config = load_config()
    vpath = config.get("vault_path")
    if not vpath or not os.path.isdir(vpath):
        print("❌ Vault path not configured. Run 'sao setup vault' first.")
        return

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from scripts.subconscious import run_session_sync, HERMES_STATE_DB
    except Exception as e:
        print(f"❌ Failed to import subconscious module: {e}")
        return

    if list_only:
        import sqlite3
        from datetime import datetime

        if not os.path.exists(HERMES_STATE_DB):
            print(f"❌ Hermes state.db not found: {HERMES_STATE_DB}")
            return
        sessions_dir = os.path.join(vpath, "Sessions")
        con = sqlite3.connect(HERMES_STATE_DB)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """
            SELECT id, title, started_at, message_count, source
            FROM sessions
            WHERE message_count > 1
            ORDER BY started_at DESC
            LIMIT 40
            """
        ).fetchall()
        con.close()
        print(f"📋 Hermes sessions (latest 40) → vault: {vpath}")
        print(f"{'STATUS':8} {'MSGS':>5}  {'SOURCE':10}  ID  TITLE")
        for r in rows:
            note = os.path.join(sessions_dir, f"{r['id']}.md")
            status = "IN_VAULT" if os.path.exists(note) else "MISSING"
            started = datetime.fromtimestamp(r["started_at"]).strftime("%m-%d %H:%M")
            title = (r["title"] or "")[:40]
            print(f"{status:8} {r['message_count']:>5}  {(r['source'] or '-'):10}  {r['id']}  {title}")
            print(f"         started {started}")
        return

    if session_id:
        print(f"🔄 Force sync session: {session_id}")
        run_session_sync(vpath, filter_session=session_id, force=True)
    else:
        run_session_sync(vpath)


def main():
    parser = argparse.ArgumentParser(description="SAO — Sira Agentic Orchestrator CLI")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="Launch all SAO services")
    start_parser.add_argument(
        "--clean-graph",
        action="store_true",
        help="Full graph rebuild: wipe graphify-out + reindex (removes stale nodes from deleted files)",
    )
    subparsers.add_parser("status", help="Show running status of SAO services")
    subparsers.add_parser("stop", help="Stop all SAO services")

    setup_parser = subparsers.add_parser("setup", help="Setup SAO configurations")
    setup_parser.add_argument("module", choices=["vault"], help="Module to setup (e.g., vault)")

    create_parser = subparsers.add_parser("create", help="Create a new Sira-Vault")
    create_parser.add_argument("module", choices=["vault"], help="Module to create (e.g., vault)")

    set_parser = subparsers.add_parser("set", help="Set SAO options")
    set_parser.add_argument("module", choices=["worker"], help="What to set (worker)")
    set_parser.add_argument("value", nargs="?", default=None, help="Worker name/cmd: sira | claude | opencode | <cli>")

    log_parser = subparsers.add_parser("log", help="Sync/list Hermes sessions into vault/Sessions/")
    log_parser.add_argument("action", nargs="?", default=None, help="Optional: list | session | <session_id>")
    log_parser.add_argument("session_id", nargs="?", default=None, help="Session id when action=session")

    args = parser.parse_args()

    if args.command == "start":
        cmd_start(clean_graph=getattr(args, "clean_graph", False))
    elif args.command == "status":
        cmd_status()
    elif args.command == "stop":
        cmd_stop()
    elif args.command == "setup":
        if args.module == "vault":
            cmd_setup_vault()
    elif args.command == "create":
        if args.module == "vault":
            cmd_create_vault()
    elif args.command == "set":
        if args.module == "worker":
            cmd_set_worker(args.value)
    elif args.command == "log":
        action = getattr(args, "action", None)
        sid = getattr(args, "session_id", None)
        if action == "list":
            cmd_log_sessions(list_only=True)
        elif action == "session":
            if not sid:
                print("Usage: sao log session <session_id>")
            else:
                cmd_log_sessions(session_id=sid)
        elif action is None:
            cmd_log_sessions()
        else:
            # allow: sao log <session_id>
            cmd_log_sessions(session_id=action)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
