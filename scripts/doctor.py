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
    port = 20477
    if _port_open(port):
        report.add("hermes_port", "PASS", f"localhost:{port} accepting connections")
    else:
        report.add(
            "hermes_port",
            "WARN",
            f"Port {port} closed — Hermes not running as SAO API (gateway may still be up elsewhere)",
        )
    # global hermes skill copy
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
            "WARN",
            f"Missing {hermes}\nOK if Hermes is global; else: sao install",
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
    for k in ("SAO_VAULT_PATH", "HERMES_STATE_DB", "SAO_HERMES_STATE_DB"):
        v = os.environ.get(k)
        lines.append(f"{k}={v or '(unset)'}")
    # unset is normal outside sao start child
    report.add("env", "INFO", "\n".join(lines) + "\n(set automatically during sao start)")


def run_health() -> Report:
    report = Report()
    check_scripts(report)
    vault = check_config(report)
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
    parser = argparse.ArgumentParser(description="SAO doctor / smoke test")
    parser.add_argument("--smoke", action="store_true", help="Run isolated smoke tests after health checks")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on WARN as well")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON report")
    args = parser.parse_args(argv)

    health = run_health()
    smoke = None
    if args.smoke:
        smoke = run_smoke()

    if args.json:
        def ser(r: Report):
            return [{"name": x.name, "level": x.level, "detail": x.detail} for x in r.results]
        out = {"health": ser(health), "smoke": ser(smoke) if smoke else None}
        print(json.dumps(out, indent=2))
    else:
        health.print_report("SAO Doctor — Health")
        if smoke:
            smoke.print_report("SAO Doctor — Smoke")

    fails = health.fails + (smoke.fails if smoke else 0)
    warns = health.warns + (smoke.warns if smoke else 0)
    if fails:
        return 1
    if args.strict and warns:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
