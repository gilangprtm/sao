#!/usr/bin/env python3
"""
SAO Subconscious Loop (Vault-Centric)

Jobs:
  sync   — compile Hermes sessions → vault/Sessions/<id>.md
  daily  — sync + write wiki/journal/YYYY-MM-DD.md
  health — light service ping

Triggered by Hermes cron or `sao log` / `sao log session <id>`.
"""

import sys
import os
import re
import json
import sqlite3
from datetime import datetime, timedelta

CONFIG_PATH = os.path.expanduser("~/.sao/config.json")
HERMES_STATE_DB = os.path.expanduser("~/AppData/Local/hermes/state.db")


def load_vault_path():
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return (json.load(f) or {}).get("vault_path")
    except Exception:
        return None


def _safe_preview(text, limit=400):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", str(text)).strip()
    return (text[:limit] + "...") if len(text) > limit else text


def _session_filepath(sessions_dir, sess_id):
    return os.path.join(sessions_dir, f"{sess_id}.md")


def _read_existing_meta(filepath):
    """Return message_count from existing session note, if any."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            head = f.read(800)
        m = re.search(r"^message_count:\s*(\d+)", head, re.M)
        return int(m.group(1)) if m else 0
    except Exception:
        return 0


def _compile_session_md(sess, messages):
    sess_id = sess["id"]
    title = sess["title"] or f"Session {sess_id}"
    started_at = datetime.fromtimestamp(sess["started_at"]).strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.fromtimestamp(sess["started_at"]).strftime("%Y-%m-%d")
    msg_count = sess["message_count"] or 0

    first_user = ""
    last_assistant = ""
    topics = []
    for m in messages:
        role = m["role"]
        content = m["content"] or ""
        if role == "user" and not first_user:
            first_user = content
        if role == "assistant" and content.strip():
            last_assistant = content
        # crude topic hints from user lines
        if role == "user" and content.strip():
            line = content.strip().split("\n")[0]
            if 12 <= len(line) <= 120 and line not in topics:
                topics.append(line)
            if len(topics) >= 5:
                break

    topics_block = "\n".join(f"- {t}" for t in topics) if topics else "- (belum diekstrak)"

    return f"""---
title: "{title.replace('"', "'")}"
date: {date_str}
started_at: "{started_at}"
session_id: "{sess_id}"
source: "{sess['source'] or 'unknown'}"
model: "{sess['model'] or 'unknown'}"
message_count: {msg_count}
status: compiled
tags: [domain/session, type/session]
---

# Session: {title}

- **ID:** `{sess_id}`
- **Waktu Mulai:** {started_at}
- **Source/Platform:** `{sess['source'] or 'unknown'}`
- **Directory:** `{sess['cwd'] or 'N/A'}`
- **Messages:** {msg_count}

## Topik (user prompts ringkas)
{topics_block}

## Pertama Ditanyakan
> {_safe_preview(first_user, 500)}

## Resolusi / Status Terakhir (Sira)
{_safe_preview(last_assistant, 800)}

## Hubungan Wiki / Tindak Lanjut
- *Tambah `[[wikilink]]` ke halaman wiki terkait jika topik ini perlu dilanjutkan.*
- *Sira: cek file ini + Graphify sebelum mengulang diskusi yang sama.*
"""


def run_session_sync(vault_path, filter_session=None, force=False):
    """
    Compile Hermes state.db sessions into vault/Sessions/<id>.md

    - New sessions → create note
    - Growing sessions (message_count naik) → rewrite note (obrolan memanjang)
    - filter_session → only one id
    """
    if not os.path.exists(HERMES_STATE_DB):
        print(f"⚠️ Hermes state.db not found at {HERMES_STATE_DB}. Session sync skipped.")
        return 0

    sessions_dir = os.path.join(vault_path, "Sessions")
    os.makedirs(sessions_dir, exist_ok=True)

    print("🔄 Syncing Hermes sessions → vault/Sessions/ ...")

    con = sqlite3.connect(HERMES_STATE_DB)
    con.row_factory = sqlite3.Row

    if filter_session:
        query = """
            SELECT id, title, started_at, message_count, source, model, cwd
            FROM sessions
            WHERE id = ?
        """
        params = (filter_session,)
    else:
        query = """
            SELECT id, title, started_at, message_count, source, model, cwd
            FROM sessions
            WHERE message_count > 1
            ORDER BY started_at DESC
        """
        params = ()

    try:
        sessions = con.execute(query, params).fetchall()
    except Exception as e:
        print(f"❌ Failed to query sessions: {e}")
        con.close()
        return 0

    created = 0
    updated = 0
    skipped = 0

    for sess in sessions:
        sess_id = sess["id"]
        filepath = _session_filepath(sessions_dir, sess_id)
        existing_count = _read_existing_meta(filepath)
        current_count = sess["message_count"] or 0

        # Skip unchanged notes unless force / filter single session
        if existing_count is not None and not force and filter_session is None:
            if existing_count == current_count:
                skipped += 1
                continue

        messages = con.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
            (sess_id,),
        ).fetchall()
        if not messages:
            skipped += 1
            continue

        content = _compile_session_md(sess, messages)
        is_new = existing_count is None
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        if is_new:
            created += 1
        else:
            updated += 1

    con.close()
    print(f"✅ Sessions: created={created}, updated={updated}, skipped={skipped}")
    return created + updated


def run_daily_digest(vault_path):
    """Write wiki/journal/YYYY-MM-DD.md and link today's session notes."""
    journal_dir = os.path.join(vault_path, "wiki", "journal")
    os.makedirs(journal_dir, exist_ok=True)

    today_str = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(journal_dir, f"{today_str}.md")
    sessions_dir = os.path.join(vault_path, "Sessions")

    today_sessions = []
    if os.path.exists(sessions_dir):
        # filenames often start with YYYYMMDD_
        prefix = today_str.replace("-", "")
        for f in sorted(os.listdir(sessions_dir)):
            if not f.endswith(".md"):
                continue
            if f.startswith(prefix) or today_str in f:
                today_sessions.append(f[:-3])

    # also scan frontmatter date: today for non-prefixed ids (cron_*, etc.)
    if os.path.exists(sessions_dir):
        for f in os.listdir(sessions_dir):
            if not f.endswith(".md"):
                continue
            sid = f[:-3]
            if sid in today_sessions:
                continue
            try:
                with open(os.path.join(sessions_dir, f), "r", encoding="utf-8") as fh:
                    head = fh.read(400)
                if f"date: {today_str}" in head:
                    today_sessions.append(sid)
            except Exception:
                pass

    tasks_dir = os.path.expanduser("~/AppData/Local/sao/tasks")
    tasks_logged = []
    if os.path.exists(tasks_dir):
        for f in os.listdir(tasks_dir):
            if f.endswith(".json") and f.startswith(today_str):
                try:
                    with open(os.path.join(tasks_dir, f), "r", encoding="utf-8") as file:
                        tasks_logged.append(json.load(file))
                except Exception:
                    pass

    content = f"""---
title: "Journal: {today_str}"
date: {today_str}
type: journal
status: canonical
tags: [domain/journal, type/journal]
---

# Sira Journal: {today_str}

## Executive Summary
Compiled by SAO subconscious. Session notes live in `Sessions/`.

## Sessions Logged Today
"""
    if not today_sessions:
        content += "- No session notes for today yet. Run `sao log`.\n"
    else:
        for sid in today_sessions:
            content += f"- [[{sid}]]\n"

    content += "\n## Tasks Done\n"
    if not tasks_logged:
        content += "- No task JSON registered today.\n"
    else:
        for t in tasks_logged:
            content += f"- **{t.get('title', 'Untitled')}** — {t.get('status', 'done')}\n"

    content += "\n## System Health\n- Subconscious daily pass completed.\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Daily journal written to: {filepath}")


def run_health_check():
    print(f"[{datetime.now()}] SAO subconscious health OK.")


if __name__ == "__main__":
    vpath = load_vault_path()
    if not vpath or not os.path.exists(vpath):
        print("❌ Vault path not set or invalid. Run 'sao setup vault' first.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python subconscious.py [daily|sync|health] [session_id]")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "daily":
        run_session_sync(vpath)
        run_daily_digest(vpath)
    elif cmd == "sync":
        filt = sys.argv[2] if len(sys.argv) > 2 else None
        run_session_sync(vpath, filter_session=filt, force=bool(filt))
    elif cmd == "health":
        run_health_check()
    else:
        print(f"Unknown command: {cmd}")
