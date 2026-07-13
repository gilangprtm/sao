#!/usr/bin/env python3
"""
SAO CLI — Sira Agentic Orchestrator
Entry point for commands: sao start, sao status, sao stop, sao setup vault, sao create vault
"""

import argparse
import subprocess
import sys
import os
import socket
import json

def get_psutil():
    try:
        import psutil
        return psutil
    except ImportError:
        print("Installing required module 'psutil'...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
        return psutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
START_SCRIPT = os.path.join(BASE_DIR, "scripts", "start.ps1")
CONFIG_PATH = os.path.expanduser("~/.sao/config.json")

SERVICES = {
    "9Router": 20128,
    "Graphify MCP": 5001,
    "Hermes Core": 8080
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        config = {"vault_path": ""}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return config
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"vault_path": ""}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def cmd_create_vault():
    print("🧠 SAO Create Vault\n")
    print("This will create a new Obsidian Vault with the Sira-Vault structure (AGENTS.md, wiki/, Philosophy/, etc.).\n")
    
    name = input("Enter the name for your new Vault (e.g., Sira-Vault): ").strip()
    if not name:
        print("❌ Vault name cannot be empty.")
        return

    base_path = os.path.expanduser("~/Documents")
    vault_path = os.path.join(base_path, name)

    if os.path.exists(vault_path):
        print(f"❌ Error: Folder '{vault_path}' already exists.")
        return

    # Create Sira-Vault structure
    try:
        os.makedirs(vault_path, exist_ok=True)
        os.makedirs(os.path.join(vault_path, "wiki", "journal"), exist_ok=True)
        os.makedirs(os.path.join(vault_path, "Philosophy"), exist_ok=True)
        os.makedirs(os.path.join(vault_path, "raw"), exist_ok=True)
        os.makedirs(os.path.join(vault_path, "ingested"), exist_ok=True)
        os.makedirs(os.path.join(vault_path, "_templates"), exist_ok=True)
        
        # Create AGENTS.md
        agents_content = """---
title: "AGENTS.md — Hermes Agent Instructions"
date: 2026-07-12
status: canonical
---

# Hermes Agent Instructions for Sira-Vault

> Dibaca otomatis oleh Hermes Agent saat workdir = Sira-Vault.

## Siapa Kamu
Kamu adalah **Sira**, AI Engineer pribadi Tuan.

## Prinsip Operasional Coding (Karpathy Guidelines)
1. **Think Before Coding**
2. **Simplicity First**
3. **Surgical Changes**
4. **Goal-Driven Execution**

## Vault Ini
Ini adalah second brain kamu. `wiki/` adalah compiled knowledge base.
"""
        with open(os.path.join(vault_path, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write(agents_content)

        # Create Philosophy/SIS.md placeholder
        with open(os.path.join(vault_path, "Philosophy", "SIS.md"), "w", encoding="utf-8") as f:
            f.write("# Sira Intelligence System (SIS)\n\n> DNA operasional Sira.\n")

        # Create Philosophy/HOM.md placeholder
        with open(os.path.join(vault_path, "Philosophy", "HOM.md"), "w", encoding="utf-8") as f:
            f.write("# Hermes Operating Manual (HOM)\n\n> Protokol operasional Sira.\n")

        # Save to config
        config = load_config()
        config["vault_path"] = vault_path
        save_config(config)

        print(f"\n✅ Vault '{name}' created successfully at:\n   {vault_path}")
        print("✅ Structure initialized (wiki/, Philosophy/, AGENTS.md).")
        print("✅ Path saved to config. You can now run 'sao start'.")

    except Exception as e:
        print(f"❌ Failed to create vault: {e}")

def cmd_setup_vault():
    print("🔧 SAO Vault Setup\n")
    print("SAO requires an Obsidian Vault to function as its brain/memory.\n")
    
    config = load_config()
    current_vault = config.get("vault_path", "")
    
    if current_vault:
        print(f"Current Vault Path: {current_vault}")
        change = input("Do you want to change this path? [y/N]: ").strip().lower()
        if change != 'y':
            print("Setup cancelled.")
            return

    while True:
        path = input("Enter the full path to your Obsidian Vault:\n> ").strip()
        
        if not path:
            print("\n⚠️ Setup cancelled.")
            break
            
        path = path.strip('"\'')
        
        if os.path.isdir(path):
            config["vault_path"] = path
            save_config(config)
            print(f"\n✅ Vault path successfully saved: {path}")
            break
        else:
            print("\n❌ Error: That directory does not exist. Please enter a valid path.")

def cmd_start():
    config = load_config()
    if not config.get("vault_path"):
        print("❌ Error: Vault path is not set.")
        print("Please run 'sao create vault' or 'sao setup vault' first.")
        sys.exit(1)
        
    print("🚀 Starting SAO (Sira Agentic Orchestrator)...")
    subprocess.run([
        "powershell.exe",
        "-ExecutionPolicy", "Bypass",
        "-File", START_SCRIPT
    ])

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
        print(f"\n📂 Target Vault: NOT CONFIGURED (Run 'sao create vault' or 'sao setup vault')")
    
    if all_ok:
        print("\n🟢 All services are running properly.")
    else:
        print("\n🔴 Some services are offline. Run 'sao start' to launch them.")

def cmd_stop():
    print("🛑 Stopping SAO services...")
    stopped_any = False
    
    psutil = get_psutil()
    for proc in psutil.process_iter(['pid', 'name']):
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
            for line in output.strip().split('\n'):
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

def main():
    parser = argparse.ArgumentParser(description="SAO — Sira Agentic Orchestrator CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("start", help="Launch all SAO services")
    subparsers.add_parser("status", help="Show running status of SAO services")
    subparsers.add_parser("stop", help="Stop all SAO services")
    
    setup_parser = subparsers.add_parser("setup", help="Setup SAO configurations")
    setup_parser.add_argument("module", choices=["vault"], help="Module to setup (e.g., vault)")

    subparsers.add_parser("create", help="Create a new Sira-Vault").add_argument("module", choices=["vault"], help="Module to create (e.g., vault)")

    args = parser.parse_args()

    if args.command == "start":
        cmd_start()
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
    else:
        parser.print_help()

if __name__ == "__main__":
    main()