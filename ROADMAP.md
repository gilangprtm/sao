# Roadmap: SAO Phase 6+ (Vault Integration & Hardening)

Berfokus menyatukan SAO sebagai mesin murni dengan Sira-Vault sebagai otak tunggal (Single Source of Truth).

---

## 🧠 Phase 6: Deep Vault Integration

1. **Subconscious V2 (Vault Journaling)**
   - Modifikasi `subconscious.py` agar tidak menyimpan ke database, melainkan mengekstrak aktivitas task harian dan menulis file markdown langsung ke `C:\Users\gilang\Documents\Sira-Vault\wiki\journal\`.
   - Gunakan format YAML frontmatter yang sesuai dengan `SCHEMA.md` di Vault.
2. **Graphify Native Tool**
   - Buat tool Python native di Hermes (`default_api:graphify_query`) yang langsung menembak localhost:5001 (MCP). 
   - Pastikan root directory Graphify MCP diarahkan absolut ke `C:\Users\gilang\Documents\Sira-Vault`.
3. **Auto-Update Index**
   - Kaitkan webhook git atau file watcher sederhana agar setiap perubahan di Vault otomatis men-trigger `graphify --update`.

## 🚀 Phase 7: Subsystem Hardening (Infrastructure)

1. **Service Manager (PM2 / Systemd / Docker)**
   - Ganti `start.ps1` dengan PM2 (lokal) atau Docker Compose (VPS).
   - Pastikan service (9Router, Graphify, Hermes) auto-restart jika crash.
2. **Upstream Sync Mechanism**
   - Buat script `sync_upstream.ps1` untuk pull repo asli (Hermes/9Router) ke folder sementara, lalu copy/patch perubahan yang relevan tanpa merusak modifikasi lokal.

## 🛠️ Phase 8: Worker Independence

1. **Worker Abstraction Layer**
   - Jangan hardcode Claude Code. Buat antarmuka `Worker` di Hermes.
2. **Open-Source Fallback (OpenCode/Cline)**
   - Siapkan fallback worker open-source (seperti OpenCode) jika Claude Code CLI dimatikan oleh Anthropic.
3. **Multi-Agent Registry**
   - Implementasi OpenHuman Agent Registry: pisahkan sub-agen menjadi `Planner`, `Coder` (Claude), dan `Reviewer`.

## 🌐 Phase 9: UI & Dashboard

1. **SAO Control Panel (Web)**
   - Buat dashboard lokal sederhana (Next.js/React) untuk melihat live-status service SAO dan visualisasi Graphify dari Sira-Vault.
2. **CEO Dashboard Sync**
   - Integrasikan task SAO dengan file state Sira-CEO di dalam Vault (`wiki/resources/sira-ceo-state.json`).