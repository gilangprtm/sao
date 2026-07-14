---
name: sira-subconscious
description: "Background cron jobs for Sira self-reflection and session sync."
tags: ["cron", "background", "maintenance", "memory"]
---

# Sira Subconscious Loop

## Purpose
Run periodic memory sync and self-reflection in the background without user intervention.

## Cron Schedule (Hermes)
- **Every 1 hour:** session sync → `vault/Sessions/` (pindah-pindah sesi dalam sehari tetap ter-compile)
- **Daily 09:00:** sync + journal `wiki/journal/YYYY-MM-DD.md` + Self-Review
- Auto-registered by `sao start` (v1.3.10+)

Requires Hermes **gateway** (or cron scheduler) running for jobs to fire.

## Functions
- **Session Sync**: Compiles Hermes conversation history (`state.db`) into `Sessions/<session_id>.md`.
- **Auto-Linking**: Links related sessions using Jaccard similarity (user never types session IDs).
- **Daily Digest**: Writes a journal entry (`wiki/journal/YYYY-MM-DD.md`) listing today's sessions and enforcing the **Sira Self-Review Check**.

## Output
All background activity is written directly to the **user vault** (`Sessions/` and `wiki/journal/` under `vault_path` from `~/.sao/config.json`). No external database is used.