# SAO Zero-Device Install Checklist

> Pakai di **device kosong** (bukan laptop Sira).  
> Sira **tidak bisa pantau** device ini.  
> Setelah selesai (atau gagal), **copy-paste seluruh output** ke Discord/chat Sira.

**Tujuan:** buktikan `install full zero → Sira hidup` (skor 6 → 9+).

**Estimasi waktu:** 20–45 menit (tergantung internet + model setup).

**OS target checklist ini:** Windows 10/11 (PowerShell).  
Linux: sama secara konsep; ganti path `AppData` → `~/.hermes`, `powershell` → bash script jika ada.

---

## 0. Siapkan laporan

Buat file teks di device baru, contoh: `Desktop\sao-zero-report.txt`

Setiap langkah: tulis **PASS / FAIL** + **paste output error** jika FAIL.

Format laporan akhir (wajib kirim ke Sira):

```text
=== SAO ZERO-DEVICE REPORT ===
Date:
OS:
Python version:
Node version:
Git version:
uv version (if any):

STEP 0 prereq: PASS/FAIL
STEP 1 npm install: PASS/FAIL
  output:
STEP 2 sao install: PASS/FAIL
  output:
STEP 3 create vault: PASS/FAIL
  vault path:
STEP 4 doctor --fresh: PASS/FAIL
  output:
STEP 5 model/provider: PASS/FAIL
  how configured:
STEP 6 sao start: PASS/FAIL
  output:
STEP 7 doctor (host): PASS/FAIL
  output:
STEP 8 sao log list: PASS/FAIL
  output:
STEP 9 chat test: PASS/FAIL
  what you said / what Sira replied:
BLOCKER (if any):
```

---

## STEP 0 — Prerequisites (sebelum SAO)

Buka **PowerShell** (bukan harus Admin kecuali diminta).

```powershell
git --version
node --version
npm --version
python --version
# optional tapi bagus:
uv --version
```

| Cek | Harus |
|-----|--------|
| Git | ada, version tercetak |
| Node | **20+** (`node -v` → v20.x / v22.x) |
| npm | ada |
| Python | **3.11+** (`python --version`) |
| Internet | bisa `ping github.com` |

**PASS jika:** semua command di atas tidak error.  
**FAIL jika:** salah satu missing → install dulu, **jangan lanjut**.

Simpan output ke report.

---

## STEP 1 — Install SAO CLI (global)

```powershell
npm uninstall -g sira-agentic-orchestrator 2>$null
npm install -g git+https://github.com/gilangprtm/sao.git
sao --help
```

| Cek | Harus |
|-----|--------|
| `npm install` | exit tanpa error fatal |
| `sao --help` | muncul daftar command (`install`, `create`, `start`, `doctor`, `log`…) |
| Ada `doctor` | ya (`sao doctor` di help) |

**PASS jika:** help tampil + ada `doctor`.  
**FAIL jika:** `sao` not recognized → PATH Node global bermasalah; restart terminal, cek `npm root -g`.

---

## STEP 2 — `sao install` (clone Hermes + Graphify)

```powershell
sao install
```

Ini lama (clone + `uv` + deps). **Jangan tutup** terminal.

| Cek | Harus |
|-----|--------|
| Selesai tanpa throw merah fatal | ya |
| Folder services muncul | lihat di mana package global terinstall |

Cari lokasi package:

```powershell
npm root -g
# contoh: C:\Users\<user>\AppData\Roaming\npm\node_modules
dir "$(npm root -g)\sira-agentic-orchestrator\services"
```

Harus ada kira-kira:
- `services\hermes\` (isi repo / .venv)
- `services\graphify\` (isi repo / .venv)

| Cek | Harus |
|-----|--------|
| `services\hermes` | folder ada, tidak kosong |
| `services\graphify` | folder ada, tidak kosong |
| Skills ke Hermes (jika install copy) | optional: `%LOCALAPPDATA%\hermes\skills\sao-*.md` |

**PASS jika:** kedua service folder ada + install selesai.  
**FAIL jika:** clone gagal / uv gagal / folder kosong → **paste full error** ke report, stop di sini.

---

## STEP 3 — Create vault

```powershell
sao create vault
```

Ikuti prompt: nama vault (contoh `Sao-Vault`).

Default biasanya: `Documents\<NamaVault>`.

| Cek | Harus |
|-----|--------|
| Folder vault ada | ya |
| `AGENTS.md` | ada |
| `Philosophy\SIS.md` + `SOM.md` | ada |
| `Sessions\` | ada |
| `raw\` `ingested\` `wiki\` | ada |
| `.graphignore` | ada |
| Config | `%USERPROFILE%\.sao\config.json` berisi `vault_path` |

Cek cepat:

```powershell
type $env:USERPROFILE\.sao\config.json
dir (Get-Content $env:USERPROFILE\.sao\config.json | ConvertFrom-Json).vault_path
```

**PASS jika:** vault + config path valid.  
**FAIL jika:** path kosong / folder partial → paste error.

---

## STEP 4 — Doctor fresh (tanpa andalkan Hermes hidup)

Dari folder package SAO **atau** mana saja jika `sao` global:

```powershell
sao doctor --fresh
```

Atau:

```powershell
cd "$(npm root -g)\sira-agentic-orchestrator"
python scripts\doctor.py --fresh
```

| Cek | Harus |
|-----|--------|
| Exit code | **0** |
| Fresh report | **0 FAIL** |
| `fresh_session_sync` | PASS |
| `fresh_agents_inject` | PASS |
| `fresh_empty_state` | PASS (tidak leak) |

**PASS jika:** exit 0 + 0 FAIL di bagian Fresh.  
**FAIL jika:** ada FAIL → **copy seluruh output doctor** ke report.

> Ini membuktikan package + memory path di device kosong.  
> Belum membuktikan Hermes API hidup.

---

## STEP 5 — Model / provider (wajib sebelum chat)

SAO **tidak** bawa API key. User setup Hermes.

Opsi A — sudah punya OpenAI/Anthropic/OpenRouter key:
```powershell
# Ikuti docs Hermes di device itu, contoh umum:
hermes setup
# atau edit config Hermes:
# %LOCALAPPDATA%\hermes\config.yaml  (atau ~/.hermes/config.yaml)
```

Opsi B — Ollama lokal:
- Install Ollama, pull model, set Hermes provider ke local base URL.

| Cek | Harus |
|-----|--------|
| Hermes config ada | file config.yaml ketemu |
| Model default terisi | bukan kosong total |
| Test minimal (jika ada) | `hermes` chat singkat / status OK |

**PASS jika:** provider terkonfigurasi (tulis cara mana di report).  
**FAIL jika:** tidak tahu cara → stop, tanya Sira; jangan paksa `sao start` berharap chat.

---

## STEP 6 — `sao start`

```powershell
sao start
```

Biarkan jalan. Catat log di terminal.

| Cek | Harus terlihat di log (kurang lebih) |
|-----|--------------------------------------|
| Vault path | dicetak, path benar |
| state.db | ketemu ATAU “not found yet” hanya sebelum Hermes pernah jalan |
| Graph update | incremental / clean attempt (boleh warn, jangan crash total) |
| Graphify MCP | “registered” / stdio di Hermes config |
| Hermes launch | proses start (port **20477** jika pakai hermes_api SAO) |

Terminal kedua (jangan tutup `sao start`):

```powershell
sao status
sao doctor
```

| Cek | Ideal |
|-----|--------|
| Hermes Core 20477 | ACTIVE (jika mode API SAO) |
| `state.db` di doctor | path valid setelah Hermes pernah create DB |
| graphify_mcp_config | PASS atau WARN jelas (bukan silent) |

**PASS jika:** Hermes hidup (port ATAU proses Hermes gateway yang Tuan pakai) + tidak crash loop.  
**FAIL jika:** start exit segera / error Python / port tidak pernah up → **paste full log start**.

> Catatan: di laptop Sira, Hermes sering **gateway Discord**, bukan port 20477.  
> Di zero-device, ikuti apa yang `sao start` launch. Tulis di report: **API 20477** atau **gateway lain**.

---

## STEP 7 — Doctor host (setelah start pernah dijalankan)

```powershell
sao doctor
```

| Cek | Target zero-device yang “hidup” |
|-----|----------------------------------|
| vault_structure | PASS |
| agents_inject | PASS |
| state_db | PASS (setelah Hermes jalan sekali) |
| graphify_mcp_config | PASS ideal; WARN = catat |
| services_*_clone | PASS jika `sao install` benar |
| hermes_port | PASS jika pakai 20477; WARN OK jika gateway beda |

**PASS jika:** 0 FAIL (WARN boleh, tapi sebutkan).  
**FAIL jika:** ada FAIL.

---

## STEP 8 — Session memory (`sao log`)

```powershell
sao log list
sao log
```

| Cek | Harus |
|-----|--------|
| `sao log list` | tidak crash; tampil state.db path |
| Setelah ada chat | session muncul; status IN_VAULT setelah `sao log` |
| Folder Sessions | file `.md` bertambah di vault |

**PASS jika:** list jalan; sync create note.  
**FAIL jika:** state.db not found setelah Hermes chat — **blocker besar**.

---

## STEP 9 — Chat test (bukti “Sira hidup”)

Lewat channel yang tersedia di device itu (CLI Hermes / Discord bot jika sudah di-setup):

1. Kirim: `halo, ini test zero-device SAO`
2. Pastikan ada balasan
3. Jalankan lagi: `sao log`
4. Cek vault `Sessions\` ada file baru / ter-update

| Cek | Harus |
|-----|--------|
| Balasan AI | ada (bukan hang total) |
| Session note | ter-update setelah `sao log` |
| Isi note | title/preview tidak kosong total |

**PASS jika:** chat + compile session.  
**FAIL jika:** chat gagal ATAU log tidak menulis Sessions.

---

## Matriks keputusan (kirim ke Sira)

| Hasil | Arti skor install full zero |
|-------|------------------------------|
| STEP 0–4 PASS, 5–9 skip | Package solid; runtime belum diuji → tetap ~6–7 |
| STEP 0–6 PASS, chat belum | Install+start OK → ~8 |
| STEP 0–9 PASS | **Zero → Sira hidup** → ~9–10 |
| Gagal di STEP 2 | Install script broken |
| Gagal di STEP 6 | Start/Hermes integration broken |
| Gagal di STEP 8–9 | Memory path broken di device nyata |

---

## Yang **tidak** perlu di device kosong (opsional nanti)

- Discord/Telegram multi-channel (boleh belakangan)
- `sao ingest` PDF besar
- Worker Claude Code
- Graphify query kompleks

Fokus zero-device: **install → vault → start → doctor → log → 1 chat**.

---

## Troubleshooting cepat

| Gejala | Cek |
|--------|-----|
| `sao` not found | restart terminal; `npm bin -g` di PATH |
| `sao install` git error | Git credential / firewall / disk full |
| `uv` missing | install script harus auto-install uv; paste error |
| doctor --fresh FAIL inject | template AGENTS rusak / package corrupt |
| start crash graphify | `python -m graphify` di venv graphify |
| state.db not found | Hermes belum pernah run; jalankan Hermes sekali |
| MCP graphify WARN | normal di awal; `sao start` harus inject; paste config.yaml snippet `mcp_servers` |

---

## Setelah selesai

1. Isi `=== SAO ZERO-DEVICE REPORT ===` di atas.  
2. Kirim ke Sira di Discord (thread SAO).  
3. **Jangan** cuma bilang “gagal” — wajib **STEP nomor + output**.  
4. Sira akan patch repo berdasarkan FAIL point, bukan tebak-tebakan.

---

## Perintah one-shot copy (ringkas)

```powershell
# 0
git --version; node --version; npm --version; python --version

# 1
npm install -g git+https://github.com/gilangprtm/sao.git
sao --help

# 2
sao install

# 3
sao create vault

# 4
sao doctor --fresh

# 5 — setup model Hermes (manual)

# 6
sao start
# terminal lain:
sao status
sao doctor

# 8
sao log list
sao log

# 9 — chat, lalu sao log lagi
```
