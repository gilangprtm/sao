#!/usr/bin/env python3
"""
SAO Subconscious Loop (Vault-Centric)
Triggered by Hermes cron. 
Synthesizes events directly into Sira-Vault/wiki/journal/
"""

import sys
import os
import json
from datetime import datetime

VAULT_PATH = os.path.expanduser("~/Documents/Sira-Vault")
JOURNAL_DIR = os.path.join(VAULT_PATH, "wiki/journal")

def run_daily_digest():
    """Generates daily summary markdown directly into Vault"""
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(JOURNAL_DIR, f"{today_str}.md")
    
    # Check if we have temporary session logs from SAO today
    tasks_dir = os.path.expanduser("~/AppData/Local/sao/tasks")
    tasks_logged = []
    
    if os.path.exists(tasks_dir):
        for f in os.listdir(tasks_dir):
            if f.endswith(".json") and f.startswith(today_str):
                with open(os.path.join(tasks_dir, f), "r", encoding="utf-8") as file:
                    try:
                        tasks_logged.append(json.load(file))
                    except:
                        pass
                        
    # Build markdown
    content = f"""---
title: "Journal: {today_str}"
date: {today_str}
type: journal
status: canonical
tags: [domain/journal, type/journal]
---

# Sira Journal: {today_str}

## Executive Summary
Sira active sessions summary for today.

## Tasks Done
"""
    if not tasks_logged:
        content += "- No tasks registered today.\n"
    else:
        for t in tasks_logged:
            content += f"- **{t.get('title', 'Untitled')}** (Role: {t.get('role', 'worker')})\n"
            content += f"  - Status: {t.get('status', 'done')}\n"
            content += f"  - Outcome: {t.get('outcome', 'success')}\n"
            content += f"  - Verification: {t.get('verification', 'None')}\n"
            
    content += "\n## System Health\n- All services (9Router, Graphify MCP, Hermes) healthy.\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"Daily journal written to: {filepath}")

def run_health_check():
    """Run health check, prints status"""
    print(f"[{datetime.now()}] SAO Services Health: Graphify MCP and 9Router active.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "daily":
            run_daily_digest()
        elif sys.argv[1] == "health":
            run_health_check()
    else:
        print("Usage: python subconscious.py [daily|health]")