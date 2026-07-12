---
name: sira-subconscious
description: "Background cron jobs for Sira self-reflection and maintenance."
tags: ["cron", "background", "maintenance"]
---

# Sira Subconscious Loop

## Purpose
Run periodic self-reflection and maintenance tasks in the background without user intervention.

## Cron Schedule (Hermes)
- Every 4 hours: `python scripts/subconscious.py health`
- Daily at 09:00: `python scripts/subconscious.py daily`

## Functions
- **Health Check**: Verify 9Router, Hermes, Graphify, and Ledger are responsive.
- **Daily Digest**: Aggregate `journal_events` from the last 24h and write a `daily_digest` event back into the ledger.
- **Weekly Skill Synthesis** (future): Analyze successful tasks and promote them to new SKILL.md files.

## Output
All background activity is recorded in `sira_ledger.db` under `event_type = daily_digest` or `health_check`.