#!/usr/bin/env python3
"""
SAO Doctor + Smoke Test

Usage:
  python scripts/doctor.py           # health check only
  python scripts/doctor.py --smoke   # health + isolated vault smoke
  sao doctor
  sao doctor --smoke

Exit codes:
  0 = all critical checks pass
  1 = one or more FAIL (critical)
  2 = WARN only (no FAIL) when --strict-warn not set → still 0 unless --strict
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Allow `python scripts/doctor.py` from repo root
PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG_ROOT not in sys.path:
    sys.path.insert(0, PKG_ROOT)


@dataclass
class CheckResult:
    name: str
    level: str  # PASS | WARN | FAIL | INFO
    detail: str


@dataclass
class Report:
    results: List[CheckResult] = field(default_factory=list)

    def add(self, name: str, level: str, detail: str):
        self.results.append(CheckResult(name, level, detail))

    @property
    def fails(self) -> int:
        return sum(1 for r in self.results if r.level == "FAIL")

    @property
    def warns(self) -> int:
        return sum(1 for r in self.results if r.level == "WARN")

    def print_report(self, title: str = "SAO Doctor"):
        icons = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌", "INFO": "ℹ️ "}
        print(f"\n{'=' * 50}")
        print(f"  {title}")
        print(f"{'=' * 50}\n")
        for r in self.results:
            icon = icons.get(r.level, "·")
            print(f"{icon} [{r.level:4}] {r.name}")
            if r.detail:
                for line in r.detail.splitlines():
                    print(f"         {line}")
        print()
        print(f"Summary: {self.fails} FAIL · {self.warns} WARN · {len(self.results)} checks")
        if self.fails == 0 and self.warns == 0:
            print("🟢 SAO looks healthy.")
        elif self.fails == 0:
            print("🟡 SAO usable, but fix WARN items for production readiness.")
        else:
            print("🔴 Critical gaps — fix FAIL items before claiming bulletproof.")
        print()


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _find_hermes_config_files() -> List[str]:
    home = os.path.expanduser("~")
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local, "hermes", "config.yaml") if local else "",
        os.path.join(home, ".hermes", "config.yaml"),
        os.path.join(home, "AppData", "Local", "hermes", "config.yaml"),
    ]
    return [p for p in candidates if p and os.path.isfile(p)]


def check_config(report: Report) -> Optional[str]:
    cfg_path = os.path.expanduser("~/.sao/config.json")
    if not os.path.isfile(cfg_path):
        report.add("sao_config", "FAIL", f"Missing {cfg_path}\nRun: sao create vault  OR  sao setup vault")
        return None
    data = _read_json(cfg_path)
    if not data:
        report.add("sao_config", "FAIL", f"Invalid JSON: {cfg_path}")
        return None
    vault = data.get("vault_path") or ""
    report.add("sao_config", "PASS", f"{cfg_path}\nvault_path={vault or '(empty)'}\nworker={data.get('worker', 'sira')}")
    if not vault:
        report.add("vault_path", "FAIL", "vault_path empty in config")
        return None
    if not os.path.isdir(vault):
        report.add("vault_path", "FAIL", f"Directory missing: {vault}")
        return None
    report.add("vault_path", "PASS", vault)
    return vault


def check_vault_structure(report: Report, vault: str):
    required = [
        "AGENTS.md",
        "Philosophy",
        "Sessions",
        "wiki",
        "raw",
        "ingested",
        ".graphignore",
    ]
    missing = []
    for rel in required:
        p = os.path.join(vault, rel)
        if not (os.path.isfile(p) or os.path.isdir(p)):
            missing.append(rel)
    if missing:
        report.add(
            "vault_structure",
            "WARN",
            "Missing: " + ", ".join(missing) + "\nRe-run create or copy from templates/vault",
        )
    else:
        report.add("vault_structure", "PASS", "AGENTS.md, Philosophy, Sessions, wiki, raw, ingested, .graphignore")

    agents = os.path.join(vault, "AGENTS.md")
    if os.path.isfile(agents):
        text = open(agents, encoding="utf-8", errors="replace").read()
        if "{{VAULT_PATH}}" in text:
            report.add("agents_inject", "WARN", "AGENTS.md still has {{VAULT_PATH}} placeholder — run sao start or bind_vault")
        elif "Vault path" in text or vault.replace("\\", "/") in text.replace("\\", "/"):
            report.add("agents_inject", "PASS", "AGENTS.md has vault path marker / absolute path")
        else:
            report.add("agents_inject", "WARN", "AGENTS.md present but no dynamic vault path line detected")


def check_pointers(report: Report, vault: str):
    home = os.path.expanduser("~")
    local = os.environ.get("LOCALAPPDATA", "")
    paths = [
        os.path.join(home, ".sao", "vault_path.txt"),
        os.path.join(home, ".hermes", "sao_vault_path.txt"),
        os.path.join(local, "hermes", "sao_vault_path.txt") if local else "",
        os.path.join(home, ".hermes", "sao_vault.json"),
        os.path.join(local, "hermes", "sao_vault.json") if local else "",
    ]
    found = [p for p in paths if p and os.path.isfile(p)]
    if not found:
        report.add("pointers", "WARN", "No sao_vault_path.txt / sao_vault.json yet — run sao start once")
        return
    detail_lines = []
    ok_match = False
    for p in found:
        try:
            raw = open(p, encoding="utf-8").read().strip()
            detail_lines.append(f"{p}")
            if p.endswith(".json"):
                data = json.loads(raw)
                vp = (data.get("vault_path") or data.get("vault_path_posix") or "").replace("\\", "/")
                if vp and vault.replace("\\", "/") in vp or vp in vault.replace("\\", "/"):
                    ok_match = True
                detail_lines.append(f"  vault={data.get('vault_path')} state={data.get('hermes_state_db')}")
            else:
                if vault.replace("\\", "/") in raw.replace("\\", "/") or raw.replace("\\", "/") in vault.replace("\\", "/"):
                    ok_match = True
                detail_lines.append(f"  → {raw[:120]}")
        except Exception as e:
            detail_lines.append(f"{p}: read error {e}")
    if ok_match:
        report.add("pointers", "PASS", "\n".join(detail_lines))
    else:
        report.add("pointers", "WARN", "Pointers exist but may not match vault:\n" + "\n".join(detail_lines))


def check_state_db(report: Report):
    try:
        from scripts.subconscious import resolve_hermes_state_db
    except Exception as e:
        report.add("state_db_resolve", "FAIL", f"Cannot import resolve_hermes_state_db: {e}")
        return None
    db = resolve_hermes_state_db()
    if not db:
        report.add("state_db", "FAIL", "state.db not found (Hermes never run? set HERMES_STATE_DB)")
        return None
    if not os.path.isfile(db):
        report.add("state_db", "FAIL", f"Resolved path missing: {db}")
        return None
    report.add("state_db", "PASS", db)
    try:
        con = sqlite3.connect(db)
        try:
            n = con.execute(
                "SELECT COUNT(*) FROM sessions WHERE message_count > 1"
            ).fetchone()[0]
        except sqlite3.Error:
            # table name may differ — still openable
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            report.add("state_db_schema", "WARN", f"sessions query failed; tables={tables[:12]}")
            con.close()
            return db
        con.close()
        report.add("state_db_schema", "PASS", f"sessions with messages: {n}")
    except Exception as e:
        report.add("state_db_schema", "FAIL", f"SQLite open/query failed: {e}")
    return db


def check_graphify_mcp_config(report: Report, vault: str):
    configs = _find_hermes_config_files()
    if not configs:
        report.add("hermes_config", "WARN", "No Hermes config.yaml found — Graphify MCP not registered yet")
        return
    report.add("hermes_config", "PASS", "\n".join(configs))
    vault_norm = vault.replace("\\", "/")
    any_graphify = False
    any_vault_match = False
    details = []
    for cfg in configs:
        try:
            text = open(cfg, encoding="utf-8", errors="replace").read()
        except Exception as e:
            details.append(f"{cfg}: read error {e}")
            continue
        has_g = bool(re.search(r"(?m)^\s*graphify\s*:", text)) or "graphify" in text.lower()
        if has_g:
            any_graphify = True
        if vault_norm in text.replace("\\", "/") or os.path.basename(vault.rstrip("\\/")) in text:
            any_vault_match = True
        # Prefer mcp_servers style (Hermes)
        style = "mcp_servers" if "mcp_servers" in text else ("mcp:" if re.search(r"(?m)^mcp\s*:", text) else "unknown")
        details.append(f"{cfg}: graphify={has_g} style={style}")
    if any_graphify and any_vault_match:
        report.add("graphify_mcp_config", "PASS", "\n".join(details))
    elif any_graphify:
        report.add(
            "graphify_mcp_config",
            "WARN",
            "graphify present but vault path may not match current vault\n"
            + "\n".join(details)
            + "\nRun: sao start (re-registers MCP)",
        )
    else:
        report.add(
            "graphify_mcp_config",
            "WARN",
            "No graphify MCP block in Hermes config\nRun: sao start\n" + "\n".join(details),
        )


def check_hermes_runtime(report: Report):
    # we don't ping port 20477 anymore; we check if the global hermes executable exists
    candidates = []
    local = os.environ.get("LOCALAPPDATA") or ""
    home = os.path.expanduser("~")
    if local:
        candidates.extend([
            os.path.join(local, "hermes", "hermes-agent", "venv", "Scripts", "hermes.exe"),
            os.path.join(local, "hermes", "bin", "hermes.exe"),
        ])
    candidates.extend([
        os.path.join(home, ".local", "bin", "hermes.exe"),
        os.path.join(home, ".hermes", "hermes-agent", "venv", "Scripts", "hermes.exe"),
        os.path.join(home, ".hermes", "bin", "hermes"),
    ])
    found = None
    for c in candidates:
        if c and os.path.isfile(c):
            found = c
            break
    if not found:
        import shutil
        found = shutil.which("hermes")

    if found:
        report.add("hermes_executable", "PASS", f"Found at {found}")
    else:
        report.add(
            "hermes_executable",
            "WARN",
            "Hermes official CLI not found. Run: sao install",
        )
    # global hermes skill copy# global hermes skill copy
    local = os.environ.get("LOCALAPPDATA", "")
    skill_dirs = [
        os.path.join(local, "hermes", "skills") if local else "",
        os.path.expanduser("~/.hermes/skills"),
    ]
    skills_found = []
    for d in skill_dirs:
        if not d or not os.path.isdir(d):
            continue
        for name in ("sao-graphify-query.md", "sira-subconscious.md"):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                skills_found.append(p)
    if skills_found:
        report.add("sao_skills_in_hermes", "PASS", "\n".join(skills_found))
    else:
        report.add(
            "sao_skills_in_hermes",
            "WARN",
            "SAO skills not in Hermes skills/ — run sao install (or copy skills/*.md)",
        )


def check_local_services(report: Report):
    hermes = os.path.join(PKG_ROOT, "services", "hermes")
    graphify = os.path.join(PKG_ROOT, "services", "graphify")
    if os.path.isdir(hermes):
        report.add("services_hermes_clone", "PASS", hermes)
    else:
        report.add(
            "services_hermes_clone",
            "INFO",
            f"Missing {hermes}\nOK: Hermes global (official install) or Desktop preferred",
        )
    if os.path.isdir(graphify):
        report.add("services_graphify_clone", "PASS", graphify)
    else:
        report.add(
            "services_graphify_clone",
            "WARN",
            f"Missing {graphify}\nGraph update needs graphify on PATH or clone",
        )
    # graphify importable?
    try:
        import importlib.util
        spec = importlib.util.find_spec("graphify")
        if spec:
            report.add("graphify_import", "PASS", f"module found: {spec.origin}")
        else:
            report.add("graphify_import", "WARN", "python -m graphify not importable on this interpreter")
    except Exception as e:
        report.add("graphify_import", "WARN", str(e))


def check_scripts(report: Report):
    for rel in (
        "scripts/subconscious.py",
        "scripts/start.ps1",
        "scripts/install.ps1",
        "scripts/ingest.py",
        "scripts/doctor.py",
        "templates/vault/AGENTS.md",
        "templates/vault/.graphignore",
    ):
        p = os.path.join(PKG_ROOT, rel)
        if os.path.isfile(p):
            report.add(f"file:{rel}", "PASS", p)
        else:
            report.add(f"file:{rel}", "FAIL", f"Missing package file: {p}")


def check_env(report: Report):
    lines = []
    for k in ("SAO_VAULT_PATH", "HERMES_STATE_DB", "SAO_HERMES_STATE_DB", "HOME", "USERPROFILE", "LOCALAPPDATA"):
        v = os.environ.get(k)
        lines.append(f"{k}={v or '(unset)'}")
    report.add("env", "INFO", "\n".join(lines) + "\n(set automatically during sao start)")


def _patch_module_paths(home: str):
    """After faking HOME, force SAO modules to use the fresh config path."""
    cfg = os.path.join(home, ".sao", "config.json")
    try:
        import cli as cli_mod
        cli_mod.CONFIG_PATH = cfg
    except Exception:
        pass
    try:
        import scripts.subconscious as sub
        sub.CONFIG_PATH = cfg
        # force re-resolve next call
        sub.HERMES_STATE_DB = sub.resolve_hermes_state_db() or ""
    except Exception:
        pass


def enter_fresh_home():
    """
    Isolate from the developer's real Hermes/SAO state.
    Returns (tmp_root, home, localappdata, old_env_snapshot).
    """
    tmp = tempfile.mkdtemp(prefix="sao-fresh-")
    home = os.path.join(tmp, "home")
    local = os.path.join(home, "AppData", "Local")
    roaming = os.path.join(home, "AppData", "Roaming")
    docs = os.path.join(home, "Documents")
    for d in (home, local, roaming, docs, os.path.join(home, ".sao"), os.path.join(local, "hermes")):
        os.makedirs(d, exist_ok=True)

    keys = (
        "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
        "LOCALAPPDATA", "APPDATA",
        "HERMES_STATE_DB", "SAO_HERMES_STATE_DB", "SAO_VAULT_PATH",
    )
    old = {k: os.environ.get(k) for k in keys}

    os.environ["HOME"] = home
    os.environ["USERPROFILE"] = home
    # Windows-style extras
    if os.name == "nt":
        # keep drive letter if present
        drive, path = os.path.splitdrive(home)
        if drive:
            os.environ["HOMEDRIVE"] = drive
            os.environ["HOMEPATH"] = path or "\\"
    os.environ["LOCALAPPDATA"] = local
    os.environ["APPDATA"] = roaming
    for k in ("HERMES_STATE_DB", "SAO_HERMES_STATE_DB", "SAO_VAULT_PATH"):
        os.environ.pop(k, None)

    _patch_module_paths(home)
    return tmp, home, local, old


def leave_fresh_home(tmp: str, old: dict):
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    # restore real module paths
    real_home = os.path.expanduser("~")
    _patch_module_paths(real_home)
    try:
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception:
        pass


def _create_mini_state_db(path: str) -> None:
    """Minimal Hermes-compatible state.db for session sync tests."""
    import time
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            user_id TEXT,
            model TEXT,
            parent_session_id TEXT,
            started_at REAL NOT NULL,
            message_count INTEGER DEFAULT 0,
            cwd TEXT,
            title TEXT
        );
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT,
            timestamp REAL NOT NULL
        );
        """
    )
    now = time.time()
    con.execute(
        "INSERT INTO sessions (id, source, started_at, message_count, title, cwd) VALUES (?,?,?,?,?,?)",
        ("smoke-sess-1", "cli", now, 3, "Fresh install smoke topic SAO vault", "/tmp"),
    )
    con.execute(
        "INSERT INTO sessions (id, source, started_at, message_count, title, cwd) VALUES (?,?,?,?,?,?)",
        ("smoke-sess-2", "cli", now - 100, 2, "Related graphify memory", "/tmp"),
    )
    msgs = [
        ("smoke-sess-1", "user", "Bagaimana cara setup SAO vault dinamis?", now - 50),
        ("smoke-sess-1", "assistant", "Pakai sao create vault lalu sao start.", now - 40),
        ("smoke-sess-1", "user", "Lanjut graphify MCP.", now - 30),
        ("smoke-sess-2", "user", "Query graphify path AGENTS ke SOM", now - 90),
        ("smoke-sess-2", "assistant", "graphify path AGENTS.md SOM.md", now - 80),
    ]
    for sid, role, content, ts in msgs:
        con.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?,?,?,?)",
            (sid, role, content, ts),
        )
    con.commit()
    con.close()


def run_fresh_install_sim() -> Report:
    """
    Simulate empty device:
      empty HOME → create vault from template → mock state.db → session sync → bind pointers
    Never touches the developer's real ~/.sao or Hermes data (env sandbox).
    """
    report = Report()
    print("\n🧊 Fresh-device simulation (isolated HOME)...\n")
    tmp, home, local, old = enter_fresh_home()
    try:
        # 1) Empty world expectations
        cfg = os.path.join(home, ".sao", "config.json")
        if os.path.isfile(cfg):
            report.add("fresh_empty_config", "FAIL", "config should not exist yet")
        else:
            report.add("fresh_empty_config", "PASS", "no ~/.sao/config.json (clean)")

        db0 = None
        try:
            from scripts.subconscious import resolve_hermes_state_db
            db0 = resolve_hermes_state_db()
        except Exception as e:
            report.add("fresh_empty_state", "WARN", str(e))
        if db0:
            report.add("fresh_empty_state", "FAIL", f"state.db leaked from host: {db0}")
        else:
            report.add("fresh_empty_state", "PASS", "no state.db visible (clean)")

        # 2) Create vault from template (non-interactive)
        vault = os.path.join(home, "Documents", "Fresh-Vault")
        tpl = os.path.join(PKG_ROOT, "templates", "vault")
        if not os.path.isdir(tpl):
            report.add("fresh_template", "FAIL", f"missing templates/vault at {tpl}")
            return report
        shutil.copytree(tpl, vault)
        for d in ("Sessions", "wiki/journal", "raw", "ingested", "Philosophy", "graphify-out", "_templates"):
            os.makedirs(os.path.join(vault, d), exist_ok=True)
        report.add("fresh_vault_create", "PASS", vault)

        from cli import bind_vault, inject_vault_into_agents_md, load_config
        bind_vault(vault, inject_agents=True)
        cfg_data = load_config()
        if cfg_data.get("vault_path") == vault or os.path.normpath(cfg_data.get("vault_path", "")) == os.path.normpath(vault):
            report.add("fresh_bind_config", "PASS", str(cfg_data.get("vault_path")))
        else:
            report.add("fresh_bind_config", "FAIL", f"config vault_path={cfg_data.get('vault_path')}")

        agents = open(os.path.join(vault, "AGENTS.md"), encoding="utf-8").read()
        if "{{VAULT_PATH}}" in agents:
            report.add("fresh_agents_inject", "FAIL", "placeholder not replaced")
        else:
            report.add("fresh_agents_inject", "PASS", "AGENTS.md injected")

        # 3) Mock Hermes state.db in fresh LOCALAPPDATA
        state_db = os.path.join(local, "hermes", "state.db")
        _create_mini_state_db(state_db)
        os.environ["HERMES_STATE_DB"] = state_db
        os.environ["SAO_HERMES_STATE_DB"] = state_db
        _patch_module_paths(home)
        from scripts.subconscious import resolve_hermes_state_db, run_session_sync
        resolved = resolve_hermes_state_db()
        if resolved and os.path.normpath(resolved) == os.path.normpath(state_db):
            report.add("fresh_state_resolve", "PASS", resolved)
        else:
            report.add("fresh_state_resolve", "FAIL", f"resolved={resolved} expected={state_db}")

        # re-bind to store hermes_state_db in config
        bind_vault(vault, inject_agents=True)

        n = run_session_sync(vault)
        sess_dir = os.path.join(vault, "Sessions")
        notes = [f for f in os.listdir(sess_dir) if f.endswith(".md")] if os.path.isdir(sess_dir) else []
        if n >= 1 and len(notes) >= 1:
            report.add("fresh_session_sync", "PASS", f"synced={n} notes={len(notes)} files={notes[:5]}")
        else:
            report.add("fresh_session_sync", "FAIL", f"synced={n} notes={notes}")

        # 4) Package scripts still present
        for rel in ("scripts/doctor.py", "scripts/subconscious.py", "bin/sao.js"):
            p = os.path.join(PKG_ROOT, rel)
            if os.path.isfile(p):
                report.add(f"fresh_pkg:{rel}", "PASS", "ok")
            else:
                report.add(f"fresh_pkg:{rel}", "FAIL", "missing")

        # 5) Prerequisites probe (informational for real empty device)
        for cmd in ("git", "node", "npm", "python", "uv"):
            found = shutil.which(cmd)
            report.add(
                f"prereq:{cmd}",
                "PASS" if found else "WARN",
                found or "not on PATH (needed for sao install on real device)",
            )

    except Exception as e:
        report.add("fresh_fatal", "FAIL", str(e))
    finally:
        leave_fresh_home(tmp, old)
    return report


def run_health(fresh_mode: bool = False) -> Report:
    report = Report()
    if fresh_mode:
        report.add(
            "mode",
            "INFO",
            "FRESH sandbox — missing vault/state is expected until install sim runs",
        )
    check_scripts(report)
    vault = check_config(report)
    # In pure fresh health (before sim), missing config is expected → downgrade FAIL noise
    if fresh_mode and not vault:
        # rewrite last config fails as INFO for readability is hard; run_fresh handles real proof
        pass
    if vault:
        check_vault_structure(report, vault)
        check_pointers(report, vault)
        check_graphify_mcp_config(report, vault)
    check_state_db(report)
    check_local_services(report)
    check_hermes_runtime(report)
    check_env(report)
    return report


def run_smoke() -> Report:
    """Isolated smoke: temp vault + inject + resolve + session sync dry.
    Does NOT permanently change ~/.sao/config.json vault_path.
    """
    report = Report()
    print("\n🔥 Smoke test (isolated temp vault)...\n")
    tmp = tempfile.mkdtemp(prefix="sao-smoke-")
    vault = os.path.join(tmp, "Smoke-Vault")
    # Snapshot real config so we can restore after pointer writes
    cfg_path = os.path.expanduser("~/.sao/config.json")
    cfg_backup = None
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg_backup = f.read()
        except Exception:
            cfg_backup = None
    try:
        from cli import (
            inject_vault_into_agents_md,
            write_vault_pointer,
            vault_path_posix,
        )
        from scripts.subconscious import resolve_hermes_state_db

        # Minimal vault from template
        tpl = os.path.join(PKG_ROOT, "templates", "vault")
        if os.path.isdir(tpl):
            shutil.copytree(tpl, vault)
        else:
            os.makedirs(vault)
            open(os.path.join(vault, "AGENTS.md"), "w", encoding="utf-8").write(
                "## Vault Ini\n\n**Vault path (dinamis):** `{{VAULT_PATH}}`\n"
            )
            for d in ("Sessions", "wiki/journal", "raw", "ingested", "Philosophy"):
                os.makedirs(os.path.join(vault, d), exist_ok=True)
            open(os.path.join(vault, ".graphignore"), "w", encoding="utf-8").write("raw/\n")

        report.add("smoke_template", "PASS", vault)

        # Inject AGENTS (temp vault only)
        ok = inject_vault_into_agents_md(vault)
        agents = open(os.path.join(vault, "AGENTS.md"), encoding="utf-8").read()
        posix = vault_path_posix(vault)
        if "{{VAULT_PATH}}" in agents:
            report.add("smoke_agents_inject", "FAIL", "placeholder not replaced")
        elif posix in agents.replace("\\", "/") or vault.replace("\\", "/") in agents.replace("\\", "/"):
            report.add("smoke_agents_inject", "PASS", f"injected path present ({ok})")
        else:
            report.add("smoke_agents_inject", "WARN", "inject ran but path string not found in AGENTS.md")

        # Pointer write tests path resolution; restore config immediately after
        write_vault_pointer(vault)
        report.add("smoke_pointer_write", "PASS", "write_vault_pointer completed (will restore config)")

        # state.db resolve
        db = resolve_hermes_state_db()
        if db and os.path.isfile(db):
            report.add("smoke_state_db", "PASS", db)
            try:
                con = sqlite3.connect(db)
                n = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
                con.close()
                report.add("smoke_state_query", "PASS", f"sessions rows={n}")
            except Exception as e:
                report.add("smoke_state_query", "WARN", str(e))
        else:
            report.add("smoke_state_db", "WARN", "no state.db — session sync cannot run yet")

        gi = os.path.join(vault, ".graphignore")
        if os.path.isfile(gi):
            report.add("smoke_graphignore", "PASS", "present")
        else:
            report.add("smoke_graphignore", "FAIL", "missing .graphignore in template copy")

        try:
            from scripts.subconscious import run_session_sync
            n = run_session_sync(vault)
            report.add("smoke_session_sync", "PASS", f"run_session_sync returned {n}")
        except Exception as e:
            report.add("smoke_session_sync", "FAIL", str(e))

    except Exception as e:
        report.add("smoke_fatal", "FAIL", str(e))
    finally:
        # Always restore user config if we overwrote vault_path
        if cfg_backup is not None:
            try:
                with open(cfg_path, "w", encoding="utf-8") as f:
                    f.write(cfg_backup)
                # Re-write pointers to real vault
                try:
                    data = json.loads(cfg_backup)
                    real_vp = data.get("vault_path")
                    if real_vp and os.path.isdir(real_vp):
                        from cli import write_vault_pointer, inject_vault_into_agents_md
                        write_vault_pointer(real_vp)
                        inject_vault_into_agents_md(real_vp)
                except Exception:
                    pass
            except Exception as e:
                report.add("smoke_config_restore", "WARN", f"Could not restore config: {e}")
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="SAO doctor / smoke / fresh-device test")
    parser.add_argument("--smoke", action="store_true", help="Isolated temp-vault smoke (restores config)")
    parser.add_argument("--fresh", action="store_true", help="Simulate empty device HOME + install path")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on WARN as well")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON report")
    args = parser.parse_args(argv)

    health = None
    smoke = None
    fresh = None

    if args.fresh:
        # Primary proof for empty-device install path
        fresh = run_fresh_install_sim()
        # Optional: also run package-only health on REAL machine after restore
        health = run_health(fresh_mode=False)
        # Keep health package checks only signal — don't double-count host hermes noise as fresh proof
    else:
        health = run_health(fresh_mode=False)

    if args.smoke and not args.fresh:
        # smoke alone on host (dev regression)
        smoke = run_smoke()
    elif args.smoke and args.fresh:
        # smoke already covered by fresh sim session sync; skip host smoke to avoid config thrash
        pass

    if args.json:
        def ser(r: Optional[Report]):
            if not r:
                return None
            return [{"name": x.name, "level": x.level, "detail": x.detail} for x in r.results]
        out = {
            "health": ser(health),
            "smoke": ser(smoke),
            "fresh": ser(fresh),
        }
        print(json.dumps(out, indent=2))
    else:
        if fresh:
            fresh.print_report("SAO Doctor — Fresh device sim")
        if health:
            title = "SAO Doctor — Health (host)" if fresh else "SAO Doctor — Health"
            health.print_report(title)
        if smoke:
            smoke.print_report("SAO Doctor — Smoke")

    fails = 0
    warns = 0
    for r in (health, smoke, fresh):
        if r:
            fails += r.fails
            warns += r.warns
    # When --fresh, host health WARNs (no services clone, port closed) are expected on CI
    # Critical path = fresh suite + package file checks
    if args.fresh and fresh is not None:
        fails = fresh.fails
        # still count package file FAILs from health
        if health:
            fails += sum(1 for x in health.results if x.level == "FAIL" and x.name.startswith("file:"))
        warns = fresh.warns

    if fails:
        return 1
    if args.strict and warns:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
