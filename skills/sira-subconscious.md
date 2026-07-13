---
name: sira-subconscious
description: "Background cron jobs for Sira self-reflection and session sync."
tags: ["cron", "background", "maintenance", "memory"]
---

# Sira Subconscious Loop

## Purpose
Run periodic memory sync and self-reflection in the background without user intervention.

## Cron Schedule (Hermes)
- Daily at 09:00: `python scripts/subconscious.py daily` (auto-registered by `sao start`)

## Functions
- **Session Sync**: Compiles Hermes conversation history (`state.db`) into `Sessions/<session_id>.md`.
- **Auto-Linking**: Links related sessions using Jaccard similarity (user never types session IDs).
- **Daily Digest**: Writes a journal entry (`wiki/journal/YYYY-MM-DD.md`) listing today's sessions and enforcing the **Sira Self-Review Check**.

## Output
All background activity is written directly to Sira-Vault (`Sessions/` and `wiki/journal/`). No external database is used.