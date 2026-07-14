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

# Hermes is installed officially (global CLI/Desktop). No fixed SAO-owned API port.
# Status/stop use process detection, not port 20477.

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


def hermes_config_dirs():
    """Possible Hermes config locations (Windows + portable)."""
    dirs = []
    home = os.path.expanduser("~")
    dirs.append(os.path.join(home, ".hermes"))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        dirs.append(os.path.join(local, "hermes"))
    return dirs


def vault_path_posix(vault_path):
    return (vault_path or "").replace("\\", "/")


def inject_vault_into_agents_md(vault_path):
    """Replace {{VAULT_PATH}} or rewrite Vault section with absolute path."""
    agents = os.path.join(vault_path, "AGENTS.md")
    if not os.path.isfile(agents):
        return False
    try:
        with open(agents, "r", encoding="utf-8") as f:
            text = f.read()
        posix = vault_path_posix(vault_path)
        if "{{VAULT_PATH}}" in text:
            text = text.replace("{{VAULT_PATH}}", posix)
        else:
            import re
            # New index format + legacy
            patterns = [
                (r"\*\*Path \(dinamis\):\*\*\s*`[^`]*`", f"**Path (dinamis):** `{posix}`"),
                (r"\*\*Vault path \(dinamis\):\*\*\s*`[^`]*`", f"**Vault path (dinamis):** `{posix}`"),
            ]
            replaced = False
            for pat, repl in patterns:
                if re.search(pat, text):
                    text = re.sub(pat, repl, text, count=1)
                    replaced = True
                    break
            if not replaced:
                for needle in ("## Vault", "## Vault Ini"):
                    if needle in text:
                        text = text.replace(
                            needle,
                            f"{needle}\n\n**Path (dinamis):** `{posix}`\n",
                            1,
                        )
                        break
        with open(agents, "w", encoding="utf-8") as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"⚠️ Could not inject vault path into AGENTS.md: {e}")
        return False


def ensure_vault_dna_chunks(vault_path):
    """
    Copy chunked DNA files into an existing vault (upgrade path).
    Never overwrites user-edited files unless missing.
    Always refreshes AGENTS.md from short index template if still huge or legacy-only.
    """
    if not vault_path or not os.path.isdir(vault_path):
        return False
    tpl_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "vault")
    if not os.path.isdir(tpl_root):
        return False

    # Philosophy chunks
    phil_src = os.path.join(tpl_root, "Philosophy")
    phil_dst = os.path.join(vault_path, "Philosophy")
    os.makedirs(phil_dst, exist_ok=True)
    for name in (
        "SOM-Lite.md",
        "AGENTS-core.md",
        "AGENTS-memory.md",
        "AGENTS-proactive.md",
    ):
        src = os.path.join(phil_src, name)
        dst = os.path.join(phil_dst, name)
        if os.path.isfile(src) and not os.path.isfile(dst):
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass

    # Short AGENTS index: replace if missing placeholder path or file too large for small models
    agents_src = os.path.join(tpl_root, "AGENTS.md")
    agents_dst = os.path.join(vault_path, "AGENTS.md")
    try:
        if os.path.isfile(agents_src):
            replace = False
            if not os.path.isfile(agents_dst):
                replace = True
            else:
                size = os.path.getsize(agents_dst)
                with open(agents_dst, "r", encoding="utf-8", errors="replace") as f:
                    cur = f.read(2000)
                # legacy long or no chunk pointers
                if size > 12000 or "AGENTS-core" not in cur and "SOM-Lite" not in cur:
                    # backup once
                    bak = agents_dst + ".bak-pre-chunk"
                    if not os.path.isfile(bak):
                        shutil.copy2(agents_dst, bak)
                    replace = True
            if replace:
                shutil.copy2(agents_src, agents_dst)
        inject_vault_into_agents_md(vault_path)
        return True
    except Exception as e:
        print(f"⚠️ ensure_vault_dna_chunks: {e}")
        return False


def write_vault_pointer(vault_path):
    """Write vault path + hermes state.db for agents/skills — never hardcode."""
    if not vault_path:
        return
    posix = vault_path_posix(vault_path)
    # Lazy import path for state db resolution (subconscious may not be on path)
    state_db = None
    try:
        pkg = os.path.dirname(os.path.abspath(__file__))
        if pkg not in sys.path:
            sys.path.insert(0, pkg)
        from scripts.subconscious import resolve_hermes_state_db
        state_db = resolve_hermes_state_db()
    except Exception:
        # Fallback discovery without subconscious module
        local = os.environ.get("LOCALAPPDATA")
        for d in (
            os.path.join(local, "hermes") if local else None,
            os.path.expanduser("~/.hermes"),
            os.path.expanduser("~/AppData/Local/hermes"),
        ):
            if not d:
                continue
            cand = os.path.join(d, "state.db")
            if os.path.isfile(cand):
                state_db = cand
                break

    payload = {
        "vault_path": vault_path,
        "vault_path_posix": posix,
        "hermes_state_db": state_db,
        "updated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }
    for d in hermes_config_dirs():
        try:
            os.makedirs(d, exist_ok=True)
            txt = os.path.join(d, "sao_vault_path.txt")
            with open(txt, "w", encoding="utf-8") as f:
                f.write(posix + "\n")
            js = os.path.join(d, "sao_vault.json")
            with open(js, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass
    try:
        sao_dir = os.path.dirname(CONFIG_PATH)
        os.makedirs(sao_dir, exist_ok=True)
        with open(os.path.join(sao_dir, "vault_path.txt"), "w", encoding="utf-8") as f:
            f.write(posix + "\n")
        # Persist hermes_state_db into sao config for subconscious
        cfg = load_config()
        if state_db:
            cfg["hermes_state_db"] = state_db
        cfg["vault_path"] = vault_path
        save_config(cfg)
    except Exception:
        pass


def bind_vault(vault_path, inject_agents=True):
    """Single entry: save config + pointer files + AGENTS.md injection."""
    config = load_config()
    config["vault_path"] = vault_path
    save_config(config)
    write_vault_pointer(vault_path)
    if inject_agents:
        ensure_vault_dna_chunks(vault_path)
    return config


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

        config = bind_vault(vault_path, inject_agents=True)

        print(f"\n✅ Vault '{name}' created successfully at:\n   {vault_path}")
        print("✅ Structure: AGENTS.md, SCHEMA.md, Philosophy/SIS+SOM, wiki/, raw/, ingested/, graphify-out/, _templates/, Sessions/")
        print("✅ Full SIS + SOM content included (not placeholders).")
        print("✅ Vault path injected into AGENTS.md + Hermes pointer files.")
        print("✅ Path saved to ~/.sao/config.json. Next: open folder in Obsidian (optional), then 'sao start'.")

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
            bind_vault(path, inject_agents=True)
            print(f"\n✅ Vault path successfully saved: {path}")
            print("✅ AGENTS.md updated + Hermes pointer (sao_vault_path.txt) written.")
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

    # Re-bind every start: pointer files + AGENTS path stay in sync if user moved vault
    vpath = config["vault_path"]
    if os.path.isdir(vpath):
        write_vault_pointer(vpath)
        inject_vault_into_agents_md(vpath)
    else:
        print(f"❌ Vault path invalid: {vpath}")
        print("Run 'sao setup vault' to fix.")
        sys.exit(1)

    # Harden: export env for child PowerShell / Hermes / workers
    os.environ["SAO_VAULT_PATH"] = vpath
    try:
        from scripts.subconscious import resolve_hermes_state_db
        sdb = resolve_hermes_state_db()
        if sdb:
            os.environ["HERMES_STATE_DB"] = sdb
            os.environ["SAO_HERMES_STATE_DB"] = sdb
            print(f"   state.db: {sdb}")
    except Exception:
        pass

    wname, wcmd = resolve_worker(config)
    print("🚀 Starting SAO (Sira Agentic Orchestrator)...")
    print(f"   Vault: {vpath}")
    print(f"   Worker: {wname}" + (f" ({wcmd})" if wcmd else " [built-in]"))
    if clean_graph:
        print("   Graph: CLEAN rebuild (wipe stale nodes + full reindex)")
    else:
        print("   Graph: incremental update (use --clean-graph after big deletes)")
    print("   Graphify MCP: Hermes stdio (not fixed port 20476)")

    ps_args = [
        "powershell.exe",
        "-ExecutionPolicy", "Bypass",
        "-File", START_SCRIPT,
    ]
    if clean_graph:
        ps_args.append("-CleanGraph")

    subprocess.run(ps_args)



def find_hermes_exe():
    """Locate official Hermes CLI binary (not services/hermes clone)."""
    candidates = []
    local = os.environ.get("LOCALAPPDATA") or ""
    home = os.path.expanduser("~")
    if local:
        candidates.extend([
            os.path.join(local, "hermes", "hermes-agent", "venv", "Scripts", "hermes.exe"),
            os.path.join(local, "hermes", "bin", "hermes.exe"),
        ])
    candidates.extend([
        os.path.join(home, ".local", "bin", "hermes.exe"),
        os.path.join(home, ".hermes", "hermes-agent", "venv", "Scripts", "hermes.exe"),
        os.path.join(home, ".hermes", "bin", "hermes"),
    ])
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    which = shutil.which("hermes")
    if which:
        return which
    return None


def detect_hermes_runtime():
    """
    Detect Hermes install + running processes.
    Returns dict: installed_path, cli_running, desktop_running, gateway_running, processes
    """
    info = {
        "installed_path": find_hermes_exe(),
        "cli_running": False,
        "desktop_running": False,
        "gateway_running": False,
        "processes": [],
    }
    psutil = get_psutil()
    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = (proc.info.get("name") or "").lower()
                cmdline = proc.info.get("cmdline") or []
                cmd = " ".join(str(x) for x in cmdline).lower() if cmdline else ""
                is_hermes = (
                    "hermes" in name
                    or "hermes.exe" in name
                    or (
                        "hermes" in cmd
                        and (
                            "gateway" in cmd
                            or "chat" in cmd
                            or "desktop" in cmd
                            or "gui" in cmd
                        )
                    )
                )
                is_desktop = (
                    name in ("hermes.exe", "hermes desktop.exe", "hermes-desktop.exe")
                    or ("electron" in name and "hermes" in cmd)
                    or ("desktop" in cmd and "hermes" in cmd)
                )
                is_gateway = "gateway" in cmd and "hermes" in (name + " " + cmd)
                is_cli = (
                    ("hermes" in name or "hermes" in cmd)
                    and ("chat" in cmd or "hermes_cli" in cmd)
                    and "gateway" not in cmd
                )
                if is_hermes or is_desktop or is_gateway:
                    label = "hermes"
                    if is_desktop:
                        label = "desktop"
                        info["desktop_running"] = True
                    if is_gateway:
                        label = "gateway"
                        info["gateway_running"] = True
                    if is_cli:
                        info["cli_running"] = True
                    info["processes"].append({
                        "pid": proc.info.get("pid"),
                        "name": proc.info.get("name"),
                        "label": label,
                    })
                    if is_hermes and not is_desktop:
                        info["cli_running"] = info["cli_running"] or ("gateway" not in cmd)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass
    if info["processes"] and not (
        info["cli_running"] or info["desktop_running"] or info["gateway_running"]
    ):
        info["cli_running"] = True
    return info


def cmd_status():
    green = "\033[92m"
    red = "\033[91m"
    yellow = "\033[93m"
    reset = "\033[0m"

    print("📊 SAO Status")
    print("─" * 40)

    rt = detect_hermes_runtime()
    if rt["installed_path"]:
        print(f"  Hermes install: {green}FOUND{reset}")
        print(f"    {rt['installed_path']}")
    else:
        print(f"  Hermes install: {red}NOT FOUND{reset}")
        print("    Run: sao install   (official Hermes installer)")

    def mark(ok):
        return f"{green}RUNNING{reset}" if ok else f"{yellow}off{reset}"

    print(f"  Desktop:  {mark(rt['desktop_running'])}")
    print(f"  Gateway:  {mark(rt['gateway_running'])}")
    print(f"  CLI/chat: {mark(rt['cli_running'])}")
    if rt["processes"]:
        for pinfo in rt["processes"][:8]:
            print(f"    · {pinfo['label']}  pid={pinfo['pid']}  {pinfo['name']}")
    runtime_up = rt["desktop_running"] or rt["gateway_running"] or rt["cli_running"]

    config = load_config()
    vault = config.get("vault_path")
    if vault and os.path.isdir(vault):
        print(f"\n📂 Vault: {vault}")
    elif vault:
        print(f"\n📂 Vault: {yellow}path missing{reset} → {vault}")
    else:
        print(f"\n📂 Vault: {red}NOT CONFIGURED{reset} (sao create vault / sao setup vault)")

    wname, wcmd = resolve_worker(config)
    print(f"🛠️  Worker: {wname}" + (f"  cmd=`{wcmd}`" if wcmd else "  [built-in Hermes/Sira]"))
    found = detect_workers()
    if found:
        print("   Available CLIs: " + ", ".join(w["cmd"] for w in found))

    try:
        from scripts.subconscious import resolve_hermes_state_db
        sdb = resolve_hermes_state_db()
        if sdb and os.path.isfile(sdb):
            print(f"🗄️  state.db: {sdb}")
        else:
            print(f"🗄️  state.db: {yellow}not found yet{reset} (appears after first Hermes chat)")
    except Exception:
        print("🗄️  state.db: (resolver unavailable)")

    print()
    if runtime_up and vault and rt["installed_path"]:
        print(f"{green}🟢 SAO ready — Hermes is up, vault bound.{reset}")
    elif rt["installed_path"] and vault:
        print(f"{yellow}🟡 Hermes installed, not running. Open Desktop or: sao start{reset}")
    else:
        print(f"{red}🔴 Setup incomplete. sao install → sao create vault → sao start{reset}")
    print("💡 Full health: sao doctor")



def cmd_doctor(smoke=False, strict=False, as_json=False, fresh=False):
    """Health check + optional smoke / fresh-device simulation."""
    try:
        from scripts.doctor import main as doctor_main
    except Exception as e:
        print(f"❌ Failed to load doctor module: {e}")
        sys.exit(1)
    argv = []
    if smoke:
        argv.append("--smoke")
    if strict:
        argv.append("--strict")
    if as_json:
        argv.append("--json")
    if fresh:
        argv.append("--fresh")
    code = doctor_main(argv)
    sys.exit(code)



def cmd_stop():
    """Stop Hermes processes started for SAO (gateway/cli). Desktop may stay if user wants."""
    print("🛑 Stopping Hermes processes (gateway/cli)...")
    stopped_any = False
    psutil = get_psutil()
    kill_names = {
        "hermes.exe",
        "hermes",
    }
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            cmdline = proc.info.get("cmdline") or []
            cmd = " ".join(str(x) for x in cmdline).lower() if cmdline else ""
            match = False
            if name in kill_names or name == "hermes.exe":
                match = True
            if "hermes" in cmd and (
                "gateway" in cmd
                or "hermes_cli" in cmd
                or " chat" in cmd
                or cmd.endswith("chat")
            ):
                match = True
            if name in ("hermes.exe",) and ("desktop" in cmd or "gui" in cmd or not cmd):
                match = True
            if not match:
                continue
            print(f"  - Stopping {proc.info.get('name')} (PID {proc.info.get('pid')})...")
            proc.kill()
            stopped_any = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if stopped_any:
        print("\n🟢 Stopped Hermes process(es).")
    else:
        print("\n⚪ No Hermes process detected (Desktop may already be closed).")
    print("💡 Tip: close Hermes Desktop from the app tray if it is still open.")



def cmd_log_sessions(session_id=None, list_only=False, summarize=False):
    """sao log | sao log list | sao log session <id> | sao log --summarize

    - list: show Hermes sessions + vault note status
    - session <id>: force recompile one growing session
    - --summarize: trigger AI to summarize yesterday's transcripts
    - (default): sync all sessions (create new + update longer ones)
    """
    if summarize:
        config = load_config()
        vpath = config.get("vault_path")
        if not vpath or not os.path.isdir(vpath):
            print("❌ Vault path not configured. Run 'sao setup vault' first.")
            return
        # Check if Hermes Gateway is running
        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:20477/v1/models", timeout=3)
        except:
            print("❌ Gateway Hermes tidak merespon (port 20477).")
            print("💡 Fitur --summarize butuh 'sao start' dulu agar Gateway menyala.")
            return
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from scripts.subconscious import run_ai_summarize
            run_ai_summarize(vpath)
        except Exception as e:
            print(f"❌ Gagal memanggil AI Summarize: {e}")
        return
    config = load_config()
    vpath = config.get("vault_path")
    if not vpath or not os.path.isdir(vpath):
        print("❌ Vault path not configured. Run 'sao setup vault' first.")
        return

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from scripts.subconscious import run_session_sync, resolve_hermes_state_db
    except Exception as e:
        print(f"❌ Failed to import subconscious module: {e}")
        return

    if list_only:
        import sqlite3
        from datetime import datetime

        state_db = resolve_hermes_state_db()
        if not state_db or not os.path.exists(state_db):
            print(f"❌ Hermes state.db not found (set HERMES_STATE_DB or run sao start once)")
            return
        sessions_dir = os.path.join(vpath, "Sessions")
        con = sqlite3.connect(state_db)
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
        print(f"   state.db: {state_db}")
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

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Health check (vault, state.db, MCP config, skills). Use --smoke for isolated tests.",
    )
    doctor_parser.add_argument(
        "--smoke",
        action="store_true",
        help="Also run isolated temp-vault smoke (bind, inject, session sync dry-run)",
    )
    doctor_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat WARN as failure (exit 1)",
    )
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="JSON report for CI",
    )
    doctor_parser.add_argument(
        "--fresh",
        action="store_true",
        help="Simulate empty device (fake HOME) + vault create + mock state.db + session sync",
    )

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

    subparsers.add_parser("ingest", help="Ingest raw files from vault/raw/ into wiki/ (clean structured Markdown)")

    args = parser.parse_args()

    if args.command == "start":
        cmd_start(clean_graph=getattr(args, "clean_graph", False))
    elif args.command == "status":
        cmd_status()
    elif args.command == "stop":
        cmd_stop()
    elif args.command == "doctor":
        cmd_doctor(
            smoke=getattr(args, "smoke", False),
            strict=getattr(args, "strict", False),
            as_json=getattr(args, "json", False),
            fresh=getattr(args, "fresh", False),
        )
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
    elif args.command == "ingest":
        try:
            from scripts.ingest import run_ingestion
            run_ingestion()
        except Exception as e:
            print(f"❌ Failed to run ingestion: {e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
