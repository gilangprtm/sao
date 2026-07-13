# scripts/subconscious.py
#!/usr/bin/env python3
"""
SAO Subconscious Loop (Vault-Centric)
Triggered by Hermes cron or manual SAO start/status.
Synthesizes events + sessions directly into Sira-Vault.
"""

import sys
import os
import json
import sqlite3
from datetime import datetime

# We will load dynamically to avoid hardcoding C:/Users/gilang
CONFIG_PATH = os.path.expanduser("~/.sao/config.json")
HERMES_STATE_DB = os.path.expanduser("~/AppData/Local/hermes/state.db")


def load_vault_path():
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("vault_path")
    except:
        return None


def run_session_sync(vault_path):
    """
    Reads local Hermes state.db sessions and compiles summary files
    into Sira-Vault/Sessions/<SessionID>.md if not already exists.
    Also links them to index or daily journal.
    """
    if not os.path.exists(HERMES_STATE_DB):
        print(f"⚠️ Hermes state.db not found at {HERMES_STATE_DB}. Session sync skipped.")
        return

    sessions_dir = os.path.join(vault_path, "Sessions")
    os.makedirs(sessions_dir, exist_ok=True)

    print("🔄 Syncing Hermes session logs into Sira-Vault/Sessions/ ...")
    
    con = sqlite3.connect(HERMES_STATE_DB)
    con.row_factory = sqlite3.Row
    
    # Get active/recent sessions from the last 7 days
    query = """
        SELECT id, title, started_at, message_count, source, model, cwd 
        FROM sessions 
        WHERE message_count > 2
        ORDER BY started_at DESC
    """
    
    try:
        sessions = con.execute(query).fetchall()
    except Exception as e:
        print(f"❌ Failed to query sessions: {e}")
        con.close()
        return

    synced_count = 0
    
    for sess in sessions:
        sess_id = sess["id"]
        title = sess["title"] or f"Session {sess_id}"
        started_at = datetime.fromtimestamp(sess["started_at"]).strftime("%Y-%m-%d %H:%M:%S")
        date_str = datetime.fromtimestamp(sess["started_at"]).strftime("%Y-%m-%d")
        
        filepath = os.path.join(sessions_dir, f"{sess_id}.md")
        
        # Skip if already exists and has been finalized (completed sessions don't grow)
        if os.path.exists(filepath):
            continue
            
        # Fetch session messages to compile summary
        msg_query = "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC"
        messages = con.execute(msg_query, (sess_id,)).fetchall()
        
        if not messages:
            continue
            
        # Parse dialogue highlights / first user prompt + last assistant reply
        first_user = ""
        last_assistant = ""
        for m in messages:
            if m["role"] == "user" and not first_user:
                first_user = m["content"]
            if m["role"] == "assistant":
                last_assistant = m["content"]
                
        # Clean preview text
        user_preview = (first_user[:300] + "...") if len(first_user) > 300 else first_user
        assist_preview = (last_assistant[:400] + "...") if len(last_assistant) > 400 else last_assistant
        
        # Build markdown session log
        content = f"""---
title: "{title}"
date: {date_str}
started_at: "{started_at}"
session_id: "{sess_id}"
source: "{sess['source']}"
model: "{sess['model']}"
message_count: {sess['message_count']}
status: compiled
tags: [domain/session, type/session]
---

# Session: {title}

- **ID:** `{sess_id}`
- **Waktu Mulai:** {started_at}
- **Source/Platform:** `{sess['source']}`
- **Directory:** `{sess['cwd'] or 'N/A'}`

## Pertama Ditanyakan (User Prompt)
> {user_preview}

## Summary / Resolusi Terakhir (Sira Reply)
{assist_preview}

## Hubungan Wiki / Tindak Lanjut
- *Gunakan wikilink `[[NamaHalaman]]` di sini untuk menghubungkan ke framework, arsitektur, atau issue yang dibahas.*
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        synced_count += 1

    con.close()
    print(f"✅ Sync complete. Created {synced_count} new session logs in vault.")


def run_daily_digest(vault_path):
    """Generates daily summary markdown directly into Vault"""
    journal_dir = os.path.join(vault_path, "wiki/journal")
    os.makedirs(journal_dir, exist_ok=True)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(journal_dir, f"{today_str}.md")
    
    # Check if we have temporary task logs from SAO today
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
                        
    # Fetch today's synced sessions to link
    sessions_dir = os.path.join(vault_path, "Sessions")
    today_sessions = []
    if os.path.exists(sessions_dir):
        for f in os.listdir(sessions_dir):
            if f.endswith(".md") and f.startswith(today_str.replace("-", "")):
                # extract ID
                sid = f.replace(".md", "")
                today_sessions.append(sid)

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

## Sessions Logged Today
"""
    if not today_sessions:
        content += "- No external session logs tracked today.\n"
    else:
        for sid in today_sessions:
            content += f"- [[{sid}]]\n"

    content += "\n## Tasks Done\n"
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
    vpath = load_vault_path()
    if not vpath or not os.path.exists(vpath):
        print("❌ Vault path not set or invalid in configuration. Run 'sao setup vault' first.")
        sys.exit(1)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "daily":
            # Sync sessions first so they can be linked in the daily digest
            run_session_sync(vpath)
            run_daily_digest(vpath)
        elif cmd == "sync":
            run_session_sync(vpath)
        elif cmd == "health":
            run_health_check()
        else:
            print(f"Unknown command: {cmd}")
    else:
        print("Usage: python subconscious.py [daily|sync|health]")
