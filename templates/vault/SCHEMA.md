---
title: "SCHEMA — Vault Operating Instructions"
date: 2026-07-13
status: canonical
---

# SCHEMA

## Folder Map

| Path | Purpose |
|------|---------|
| `Philosophy/` | DNA: SIS + SOM (jangan dihapus) |
| `wiki/` | Compiled knowledge base |
| `wiki/journal/` | Daily digests (SAO subconscious) |
| `raw/` | Incoming unprocessed sources |
| `ingested/` | Processed source archive |
| `graphify-out/` | Graphify index output (`graph.json`, report) |
| `_templates/` | Note / PRD templates |
| `AGENTS.md` | Agent rules (auto-read by Hermes) |

## Rules

1. Every `wiki/` page needs YAML frontmatter
2. Use `[[wikilinks]]` between notes
3. Prefer update over create-duplicate
4. Journal files: `wiki/journal/YYYY-MM-DD.md`
5. Drop new sources into `raw/`; after processing move to `ingested/`
6. Do not hand-edit `graphify-out/` — regenerate via `graphify update`
