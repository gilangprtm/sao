#!/usr/bin/env python3
"""
SAO CLI — Sira Agentic Orchestrator
Entry point for commands: sao start, sao status, sao stop, sao setup vault
"""

import argparse
import subprocess
import sys
import os
import socket
import psutil
import json

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

def cmd_setup_vault():
    print("🔧 SAO Vault Setup\n")
    print("SAO requires an Obsidian Vault to function as its brain/memory.")
    print("If you haven't created one, please download Obsidian (https://obsidian.md) and create an empty Vault first.\n")
    
    config = load_config()
    current_vault = config.get("vault_path", "")
    
    if current_vault:
        print(f"Current Vault Path: {current_vault}")
        change = input("Do you want to change this path? [y/N]: ").strip().lower()
        if change != 'y':
            print("Setup cancelled.")
            return

    while True:
        path = input("Enter the full path to your Obsidian Vault (or press Enter to skip for now):\n> ").strip()
        
        if not path:
            print("\n⚠️ Vault setup skipped. You must run 'sao setup vault' before starting SAO.")
            break
            
        # Remove quotes if user pasted them
        path = path.strip('"\'')
        
        if os.path.isdir(path):
            config["vault_path"] = path
            save_config(config)
            print(f"\n✅ Vault path successfully saved: {path}")
            
            # Initialize basic vault structure if it doesn't exist
            journal_path = os.path.join(path, "wiki", "journal")
            agents_path = os.path.join(path, "AGENTS.md")
            
            if not os.path.exists(journal_path):
                os.makedirs(journal_path, exist_ok=True)
                print("   - Created wiki/journal/ directory")
            
            if not os.path.exists(agents_path):
                with open(agents_path, "w", encoding="utf-8") as f:
                    f.write("# Sira-Vault\nDefault Vault for SAO. Add your rules here.\n")
                print("   - Created default AGENTS.md")
                
            print("\nVault is ready for SAO!")
            break
        else:
            print("\n❌ Error: That directory does not exist. Please enter a valid path.")

def cmd_start():
    config = load_config()
    if not config.get("vault_path"):
        print("❌ Error: Vault path is not set.")
        print("Please run 'sao setup vault' first to connect SAO to your Obsidian Vault.")
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
        print(f"\n📂 Target Vault: NOT CONFIGURED (Run 'sao setup vault')")
    
    if all_ok:
        print("\n🟢 All services are running properly.")
    else:
        print("\n🔴 Some services are offline. Run 'sao start' to launch them.")

def cmd_stop():
    print("🛑 Stopping SAO services...")
    stopped_any = False
    
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
    else:
        parser.print_help()

if __name__ == "__main__":
    main()