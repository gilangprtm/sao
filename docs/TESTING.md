# Optional CI — NOT required for SAO confidence

GitHub Actions on this account may be **locked (billing)**. Do **not** treat green/red Actions as the gate.

## Source of truth: local doctor

```bash
# From repo root (any machine with Python)
python scripts/doctor.py --fresh
# or after global install:
sao doctor --fresh
```

- Exit `0` → fresh-device path OK  
- Exit `1` → FAIL list must be fixed before claiming ready  

Host-only regression (your laptop with Hermes):

```bash
python scripts/doctor.py
python scripts/doctor.py --smoke
```

## If GitHub Actions becomes available later

Workflow: `.github/workflows/ci.yml` (windows + ubuntu `--fresh`).  
Enable only when billing is fixed — never block development on it.

## Local scheduled monitor (recommended)

Hermes cron or Windows Task Scheduler, daily:

```text
python <SAO_REPO>/scripts/doctor.py --fresh
```

Deliver stdout on failure only (watchdog style) if you wire a script with empty stdout on success.
