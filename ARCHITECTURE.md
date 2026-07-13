# Sira Agentic Orchestrator (SAO) Architecture

**Visi**: AI Operating System dengan Permanent Memory. Single Source of Truth = Sira-Vault.

**Prinsip Utama**:
- **Permanent Memory**: AI tidak pernah lupa. Session di-compile, Graphify mengindeks relasi antar session dan wiki. Context window terbatas, namun ingatan abadi.
- **Vault-Centric**: Tidak ada database terselubung. Otak AI (Semantic, Procedural, Episodic) 100% berada di Markdown Vault.
- **Worker Optional**: Core orchestrator mandiri. Worker eksternal (Claude Code) bersifat opsional.
- **Subconscious Loop 24/7**: Cron auto-sync session dan auto-write journal.

---

## 🏗️ Komponen

| Service | Bahasa | Port | Peran |
|---------|--------|------|-------|
| **Hermes** | Python | 20477 | Brain. Commander. Cron. Orchestrator utama |
| **Graphify** | Python | 20476 | Knowledge graph MCP — **Katalog & Index Vault** |
| **Worker** *(opsional)* | *CLI* | - | Executor coding (misal: Claude Code, OpenCode). Jika kosong, Hermes merangkap sebagai worker (`sira`). |

---

## 🧠 Memori Terpadu (Sira-Vault)

SAO mengingat dan beroperasi melalui tiga pintu:

1. **System Prompt (Otomatis)**
   - `AGENTS.md` dibaca otomatis saat aktif di Vault. Berisi DNA SIS/SOM dan aturan memory continuity.
2. **Graphify MCP (Spasial)**
   - Saat session baru dibuka, AI query Graphify untuk menelusuri session lama dan wiki tanpa token bloat.
3. **Sessions & Journal (Episodik)**
   - Chat lama dikompilasi (summary) ke `Sessions/<id>.md` lengkap dengan auto-link session terkait.
   - Ditulis oleh Subconscious Loop ke `wiki/journal/` sebagai rangkuman harian.

---

## 🔄 Memory Flow (Cara SAO Tidak Pernah Lupa)

1. **User Chat** di Discord / Telegram / TUI.
2. **SAO Log** (`sao log` atau cron daily) membaca `state.db` Hermes.
3. SAO mengompilasi obrolan menjadi file Markdown ringkas (`Sessions/<session_id>.md`).
4. **Auto-Link**: Algoritma Jaccard similarity mengaitkan file session baru ini dengan session lama yang relevan (misal: membahas topik repo yang sama 6 bulan lalu).
5. **Graphify Update**: `sao start` meng-update katalog graph JSON secara inkremental.
6. **Recall**: Di hari lain, saat user bertanya topik lama, Sira mencari via Graphify, menemukan link spasial antar session, dan melanjutkan obrolan secara natural tanpa user harus mengetik ID session.

---

## ⏰ Subconscious Loop (Cron)

| Interval | Tugas |
|----------|-------|
| Setiap 4 jam | Health check service |
| 09:00 | **Subconscious Daily**: Sync sessions baru ke vault + tulis `wiki/journal/YYYY-MM-DD.md` |
| Saat `sao start` | `graphify update` (inkremental update index Vault agar selalu fresh) |

---

## 📂 Folder Struktur (Mesin)

```
sao/
├── ARCHITECTURE.md
├── ROADMAP.md
├── cli.py               ← CLI Engine (`sao start|log|status|setup`)
├── bin/
│   └── sao.js           ← NPM global wrapper
├── services/
│   ├── hermes/
│   └── graphify/        ← Index engine untuk Sira-Vault
├── scripts/
│   ├── start.ps1
│   ├── install.ps1
│   └── subconscious.py  ← Auto-link sessions & daily digest
└── templates/
    └── vault/           ← Template DNA (SIS, SOM, AGENTS)
```
