---
title: "AGENTS — Proactive Rules"
date: 2026-07-14
status: canonical
---

# AGENTS-proactive

## Wajib

| Rule | Aksi |
|------|------|
| PRE-CHECK MEMORY | Chat lama → `session_search` |
| PRE-CHECK VAULT | Struktur/codebase → `sao-graphify-query` (jangan pakai grep manual) |
| GRILLING | Tantang ambiguitas & edge case |
| AUTO-REFLECTION | Task kompleks → `wiki/journal/` YAML |
| HARD-GATE | No scaffold sebelum desain disetujui |
| VERIFICATION | Klaim sukses + bukti terminal bareng |
| DEBUG 3x | Stop & diskusikan setelah 3 gagal |

## Jangan

- Pakai `grep` / `rg` manual di Vault. Graphify sudah mengindeks relasi `graphify-out/graph.json` — pakailah MCP.
- Yes-man tanpa tantangan  
- Dump raw chat ke vault  
- Minta user ingat session ID  
- Rename/hapus DNA tanpa izin  
- Spekulatif over-engineering  

## Sebelum tulis ke vault

1. Cek `SCHEMA.md`  
2. Cek duplikat `wiki/` + `Sessions/`  
3. Template `_templates/`  
4. Update `wiki/index.md` jika halaman baru
