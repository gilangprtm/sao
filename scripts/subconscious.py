#!/usr/bin/env python3
"""
SAO Subconscious Loop (Vault-Centric)

Jobs:
  sync   — compile Hermes sessions → vault/Sessions/<id>.md
           (+ auto-link related sessions — NO user input needed)
  daily  — sync + write wiki/journal/YYYY-MM-DD.md
  health — light service ping

Triggered by Hermes cron or `sao log` / `sao log session <id>`.

Design:
  User may open NEW sessions (context window limits). Sira must still
  recall prior work WITHOUT forcing user back to old session IDs.
  Linking is automatic via title/topic/token overlap + Hermes parent_session_id.
"""

import sys
import os
import re
import json
import sqlite3
from datetime import datetime
from collections import defaultdict

CONFIG_PATH = os.path.expanduser("~/.sao/config.json")

# tokens too common to use for relatedness
_STOP = {
    "the", "and", "for", "with", "this", "that", "from", "into", "your", "have",
    "yang", "dan", "atau", "dengan", "untuk", "dari", "pada", "ini", "itu",
    "saya", "kamu", "kita", "ada", "sudah", "belum", "bisa", "mau", "akan",
    "session", "sira", "hermes", "sao", "user", "tuan", "please", "help",
}


def load_vault_path():
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return (json.load(f) or {}).get("vault_path")
    except Exception:
        return None


def resolve_hermes_state_db():
    """
    Find Hermes state.db without hardcoding one profile path.
    Order:
      1. HERMES_STATE_DB env
      2. SAO_HERMES_STATE_DB env
      3. ~/.sao/config.json → hermes_state_db
      4. ~/.hermes/sao_vault.json / %LOCALAPPDATA%/hermes/sao_vault.json → hermes_state_db
      5. Common Hermes profile dirs that contain state.db
    """
    for key in ("HERMES_STATE_DB", "SAO_HERMES_STATE_DB"):
        env = os.environ.get(key)
        if env and os.path.isfile(env):
            return env

    # config / pointer files
    candidates_meta = [CONFIG_PATH]
    home = os.path.expanduser("~")
    candidates_meta.append(os.path.join(home, ".hermes", "sao_vault.json"))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates_meta.append(os.path.join(local, "hermes", "sao_vault.json"))
    for meta in candidates_meta:
        if not os.path.isfile(meta):
            continue
        try:
            with open(meta, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            p = data.get("hermes_state_db") or data.get("state_db")
            if p and os.path.isfile(p):
                return p
        except Exception:
            pass

    # Well-known locations (Windows + Unix Hermes layouts)
    search_dirs = []
    if local:
        search_dirs.append(os.path.join(local, "hermes"))
    search_dirs.append(os.path.join(home, ".hermes"))
    search_dirs.append(os.path.join(home, "AppData", "Local", "hermes"))
    # Profile subdirs: ~/.hermes/profiles/<name>/
    profiles = os.path.join(home, ".hermes", "profiles")
    if os.path.isdir(profiles):
        for name in os.listdir(profiles):
            search_dirs.append(os.path.join(profiles, name))
    if local:
        profiles2 = os.path.join(local, "hermes", "profiles")
        if os.path.isdir(profiles2):
            for name in os.listdir(profiles2):
                search_dirs.append(os.path.join(profiles2, name))

    found = []
    for d in search_dirs:
        db = os.path.join(d, "state.db")
        if os.path.isfile(db):
            try:
                found.append((os.path.getmtime(db), db))
            except OSError:
                found.append((0, db))
    if found:
        found.sort(key=lambda x: x[0], reverse=True)
        return found[0][1]
    return None


# Resolved at import for backward-compat imports; re-resolve inside jobs too.
HERMES_STATE_DB = resolve_hermes_state_db() or os.path.expanduser(
    "~/AppData/Local/hermes/state.db"
)


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


def _tokens(text):
    if not text:
        return set()
    words = re.findall(r"[a-zA-Z0-9_\-]{3,}", text.lower())
    return {w for w in words if w not in _STOP and not w.isdigit()}


def _extract_session_signals(sess, messages):
    """Build searchable signals for auto-related detection."""
    title = sess["title"] or ""
    first_user = ""
    topics = []
    for m in messages:
        role = m["role"]
        content = m["content"] or ""
        if role == "user" and not first_user:
            first_user = content
        if role == "user" and content.strip():
            line = content.strip().split("\n")[0]
            # strip discord prefix like [enki]
            line = re.sub(r"^\[[^\]]+\]\s*", "", line)
            if 8 <= len(line) <= 140 and line not in topics:
                topics.append(line)
            if len(topics) >= 6:
                break

    bag = _tokens(title)
    bag |= _tokens(first_user[:500])
    for t in topics:
        bag |= _tokens(t)

    last_assistant = ""
    for m in reversed(messages):
        if m["role"] == "assistant" and (m["content"] or "").strip():
            last_assistant = m["content"]
            break

    return {
        "title": title,
        "first_user": first_user,
        "topics": topics,
        "tokens": bag,
        "last_assistant": last_assistant,
        "parent_session_id": sess["parent_session_id"] if "parent_session_id" in sess.keys() else None,
    }


def _score_related(a_tokens, b_tokens, a_title, b_title):
    if not a_tokens or not b_tokens:
        return 0.0
    inter = a_tokens & b_tokens
    if not inter:
        # title soft match
        at = _tokens(a_title)
        bt = _tokens(b_title)
        inter = at & bt
        if not inter:
            return 0.0
    union = a_tokens | b_tokens
    jaccard = len(inter) / max(len(union), 1)
    # boost if several meaningful overlaps
    boost = min(len(inter), 5) * 0.03
    return jaccard + boost


def _find_related(sess_id, signals, catalog, limit=5):
    """
    Auto-find related past sessions. User never provides IDs.
    Returns list of (other_id, score, title).
    """
    # hard link: Hermes parent_session_id
    related = []
    parent = signals.get("parent_session_id")
    if parent and parent in catalog and parent != sess_id:
        related.append((parent, 1.0, catalog[parent]["title"] or parent))

    scored = []
    for other_id, meta in catalog.items():
        if other_id == sess_id:
            continue
        if parent and other_id == parent:
            continue
        score = _score_related(
            signals["tokens"],
            meta["tokens"],
            signals["title"],
            meta["title"],
        )
        if score >= 0.12:  # threshold: weak-but-real overlap
            scored.append((other_id, score, meta["title"] or other_id))

    scored.sort(key=lambda x: x[1], reverse=True)
    for item in scored[:limit]:
        if item[0] not in [r[0] for r in related]:
            related.append(item)
    return related[:limit]


def _compile_session_md(sess, messages, related=None):
    sess_id = sess["id"]
    title = sess["title"] or f"Session {sess_id}"
    started_at = datetime.fromtimestamp(sess["started_at"]).strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.fromtimestamp(sess["started_at"]).strftime("%Y-%m-%d")
    msg_count = sess["message_count"] or 0

    signals = _extract_session_signals(sess, messages)
    topics = signals["topics"]
    first_user = signals["first_user"]
    last_assistant = signals["last_assistant"]
    topics_block = "\n".join(f"- {t}" for t in topics) if topics else "- (belum diekstrak)"

    related = related or []
    parent = signals.get("parent_session_id")

    # frontmatter related ids (machine-readable)
    related_ids = [r[0] for r in related]
    related_yaml = json.dumps(related_ids, ensure_ascii=False)

    related_block = ""
    if related:
        lines = []
        for rid, score, rtitle in related:
            tag = "parent" if rid == parent else f"sim={score:.2f}"
            lines.append(f"- [[{rid}]] — {rtitle} ({tag})")
        related_block = "\n".join(lines)
    else:
        related_block = "- (belum terdeteksi session terkait)"

    continues_from = parent or (related_ids[0] if related_ids else "")

    return f"""---
title: "{title.replace('"', "'")}"
date: {date_str}
started_at: "{started_at}"
session_id: "{sess_id}"
source: "{sess['source'] or 'unknown'}"
model: "{sess['model'] or 'unknown'}"
message_count: {msg_count}
continues_from: "{continues_from}"
related_sessions: {related_yaml}
status: compiled
tags: [domain/session, type/session]
---

# Session: {title}

- **ID:** `{sess_id}`
- **Waktu Mulai:** {started_at}
- **Source/Platform:** `{sess['source'] or 'unknown'}`
- **Directory:** `{sess['cwd'] or 'N/A'}`
- **Messages:** {msg_count}

## Related Sessions (auto-detected)
{related_block}

> User **tidak** perlu tahu session ID. Sira pakai block ini untuk lanjut topik di session baru tanpa memaksa user balik ke thread lama.

## Topik (user prompts ringkas)
{topics_block}

## Pertama Ditanyakan
> {_safe_preview(first_user, 500)}

## Resolusi / Status Terakhir (Sira)
{_safe_preview(last_assistant, 800)}

## Hubungan Wiki / Tindak Lanjut
- *Tambah `[[wikilink]]` ke halaman wiki terkait jika topik ini perlu dilanjutkan.*
- *Sira: baca related sessions di atas + Graphify — lanjut natural, jangan redirect user ke session lama.*
"""


def _build_catalog(con, sessions):
    """Preload tokens for relatedness across all sessions being synced."""
    catalog = {}
    for sess in sessions:
        sid = sess["id"]
        messages = con.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT 40",
            (sid,),
        ).fetchall()
        signals = _extract_session_signals(sess, messages)
        catalog[sid] = {
            "title": signals["title"],
            "tokens": signals["tokens"],
            "parent": signals.get("parent_session_id"),
            "messages": messages,  # reuse if short
            "started_at": sess["started_at"],
        }
    return catalog


def run_session_sync(vault_path, filter_session=None, force=False):
    """
    Compile Hermes state.db sessions into vault/Sessions/<id>.md

    - New sessions → create note
    - Growing sessions (message_count naik) → rewrite note
    - Auto-link related sessions (NO user input / session IDs required)
    """
    global HERMES_STATE_DB
    state_db = resolve_hermes_state_db()
    if state_db:
        HERMES_STATE_DB = state_db
    if not state_db or not os.path.exists(state_db):
        print(f"⚠️ Hermes state.db not found (checked env, ~/.sao, ~/.hermes, LOCALAPPDATA). Session sync skipped.")
        return 0

    sessions_dir = os.path.join(vault_path, "Sessions")
    os.makedirs(sessions_dir, exist_ok=True)

    print(f"🔄 Syncing Hermes sessions → vault/Sessions/ (db: {state_db})...")

    con = sqlite3.connect(state_db)
    con.row_factory = sqlite3.Row

    # Always load a broader catalog for relatedness (even when filtering one id)
    catalog_query = """
        SELECT id, title, started_at, message_count, source, model, cwd, parent_session_id
        FROM sessions
        WHERE message_count > 1
        ORDER BY started_at DESC
        LIMIT 200
    """
    try:
        all_sessions = con.execute(catalog_query).fetchall()
    except Exception:
        # older schema without parent_session_id
        all_sessions = con.execute(
            """
            SELECT id, title, started_at, message_count, source, model, cwd
            FROM sessions
            WHERE message_count > 1
            ORDER BY started_at DESC
            LIMIT 200
            """
        ).fetchall()

    if filter_session:
        sessions = [s for s in all_sessions if s["id"] == filter_session]
        if not sessions:
            # try direct fetch
            try:
                row = con.execute(
                    "SELECT id, title, started_at, message_count, source, model, cwd, parent_session_id FROM sessions WHERE id = ?",
                    (filter_session,),
                ).fetchone()
            except Exception:
                row = con.execute(
                    "SELECT id, title, started_at, message_count, source, model, cwd FROM sessions WHERE id = ?",
                    (filter_session,),
                ).fetchone()
            sessions = [row] if row else []
    else:
        sessions = all_sessions

    if not sessions:
        print("⚪ No sessions to sync.")
        con.close()
        return 0

    catalog = _build_catalog(con, all_sessions)

    created = 0
    updated = 0
    skipped = 0

    for sess in sessions:
        sess_id = sess["id"]
        filepath = _session_filepath(sessions_dir, sess_id)
        existing_count = _read_existing_meta(filepath)
        current_count = sess["message_count"] or 0

        if existing_count is not None and not force and filter_session is None:
            if existing_count == current_count:
                skipped += 1
                continue

        # full messages for the note body
        messages = con.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
            (sess_id,),
        ).fetchall()
        if not messages:
            skipped += 1
            continue

        signals = _extract_session_signals(sess, messages)
        # refresh catalog entry with full signals
        catalog[sess_id] = {
            "title": signals["title"],
            "tokens": signals["tokens"],
            "parent": signals.get("parent_session_id"),
            "messages": messages[:40],
            "started_at": sess["started_at"],
        }
        related = _find_related(sess_id, signals, catalog, limit=5)

        content = _compile_session_md(sess, messages, related=related)
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
        prefix = today_str.replace("-", "")
        for f in sorted(os.listdir(sessions_dir)):
            if not f.endswith(".md"):
                continue
            if f.startswith(prefix) or today_str in f:
                today_sessions.append(f[:-3])

    if os.path.exists(sessions_dir):
        for f in os.listdir(sessions_dir):
            if not f.endswith(".md"):
                continue
            sid = f[:-3]
            if sid in today_sessions:
                continue
            try:
                with open(os.path.join(sessions_dir, f), "r", encoding="utf-8") as fh:
                    head = fh.read(500)
                if f"date: {today_str}" in head:
                    today_sessions.append(sid)
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
Related sessions are **auto-linked** — user never types session IDs.

## Sessions Logged Today
"""
    if not today_sessions:
        content += "- No session notes for today yet. Run `sao log`.\n"
    else:
        for sid in today_sessions:
            content += f"- [[{sid}]]\n"

    content += "\n## System Health\n- Subconscious daily pass completed.\n"

    content += """
## Sira Self-Review Check
- [ ] Apakah kemarin ada task kompleks yang selesai?
- [ ] Jika ada, apakah Reflection YAML sudah ditulis di atas?
- [ ] Apakah insight baru dari bug/task kemarin sudah dipindah ke `wiki/` KB?
- [ ] Apakah Sira melakukan *Grilling* atau sekadar *Yes-Man* kemarin?
> Sira, jika ada kotak yang kosong/belum dilakukan dari task kemarin, segera lakukan perbaikan sekarang di awal session hari ini.
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Daily journal written to: {filepath}")


def run_health_check():
    print(f"[{datetime.now()}] SAO subconscious health OK.")


if __name__ == "__main__":
    # Support: python subconscious.py daily
    #          python sao_subconscious.py   (cron no_agent may pass no args — default daily)
    vpath = load_vault_path()
    if not vpath or not os.path.exists(vpath):
        print("❌ Vault path not set or invalid. Run 'sao setup vault' first.")
        sys.exit(1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "daily"

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
        print("Usage: python subconscious.py [daily|sync|health] [session_id]")
