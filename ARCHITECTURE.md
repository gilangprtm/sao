# Sira Agentic Orchestrator (SAO) Architecture

**Visi**: Personal AI Operating System lokal. Self-improving. Single Source of Truth = Sira-Vault.

**Prinsip**:
- Local-first (semua data di mesin Tuan)
- 1 Captain (Hermes) — sub-agen eksekutor (Claude Code)
- Subconscious loop 24/7
- **Vault-Centric Memory**: Tidak ada database eksternal. Sira-Vault adalah satu-satunya memori persisten (Semantic, Procedural, Episodic).

---

## Komponen

| Service | Bahasa | Port | Peran |
|---------|--------|------|-------|
| **Hermes** | Python | 20477 | Commander. UI. Skill. Cron. Orchestrator |
| **9Router** | TypeScript | 20475 | AI Gateway. Token saving. Auto-fallback |
| **Claude Code** | Node.js | CLI | Development loop otonom (subprocess) |
| **Graphify** | Python | 20476 | Knowledge graph codebase (MCP) — **Katalog & Index Vault** |

---

## Memori Terpadu (Sira-Vault)

SAO membaca memori melalui tiga pintu:

1. **System Prompt (Otomatis)**
   - `AGENTS.md` dibaca otomatis saat aktif di Vault. Berisi DNA SIS/HOM.
2. **Graphify MCP (Spasial)**
   - Query Graphify saat butuh menelusuri ratusan file `wiki/` tanpa token bloat.
3. **Daily Journal (Episodik)**
   - Ditulis oleh Subconscious Loop ke `wiki/journal/`. Menggantikan fungsi database log (ledger).

---

## Subconscious Loop (Cron)

| Interval | Tugas |
|----------|-------|
| Setiap 4 jam | Health check service |
| 09:00 | Synthesize event harian → tulis ke `wiki/journal/YYYY-MM-DD.md` di Vault |
| Git commit | `graphify --update` (inkremental update index Vault) |

---

## Folder Struktur (Mesin)

```
sao/
├── ARCHITECTURE.md
├── ROADMAP.md
├── services/
│   ├── hermes/
│   ├── 9router/
│   └── graphify/        ← Index engine untuk Sira-Vault
├── scripts/
│   ├── start.ps1
│   ├── install.ps1
│   └── subconscious.py
└── skills/
```

---

## Alur Kerja

1. Tuan perintah SAO (Hermes)
2. SAO baca `AGENTS.md` (Aturan SIS/HOM)
3. Jika butuh relasi konteks → SAO query Graphify MCP (target: `C:\Users\gilang\Documents\Sira-Vault`)
4. Delegasi task ke Claude Code (via 9Router)
5. Selesai → Subconscious Loop mencatat hasil ke `wiki/journal/` di dalam Vault.