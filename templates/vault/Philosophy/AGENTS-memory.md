---
title: "AGENTS — Memory Continuity"
date: 2026-07-14
status: canonical
---

# AGENTS-memory

## Vault path

Diisi SAO: lihat root `AGENTS.md` → `{{VAULT_PATH}}`.  
Sumber: `~/.sao/config.json` → `vault_path`. **Jangan hardcode.**

## Layout

| Folder | Isi |
|--------|-----|
| `wiki/` | knowledge compiled |
| `Sessions/` | ringkasan chat Hermes |
| `Philosophy/` | DNA (SIS, SOM-Lite, SOM) |
| `raw/` → `ingested/` | pipeline `sao ingest` |
| `graphify-out/` | index graph |

## Continuity (user tidak perlu session ID)

1. Session baru = normal (context window).  
2. Topik lama → diam-diam: `Sessions/` + Graphify + `wiki/`.  
3. Lanjut natural; jangan paksa thread lama / minta ID.  
4. Sync: subconscious **tiap 1 jam** + daily 09:00; `sao log` = manual force.

## Auto-link

`related_sessions` / `continues_from` di note session — pakai untuk recall, jangan dump ke user.
