#!/usr/bin/env node

const { execSync, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const args = process.argv.slice(2);
const command = args[0] || 'help';
const SAO_DIR = path.resolve(__dirname, '..');
const cliPath = path.join(SAO_DIR, 'cli.py');

function exists(p) {
    try { return fs.existsSync(p); } catch { return false; }
}

function tryCmd(cmd, cmdArgs) {
    const r = spawnSync(cmd, cmdArgs, { encoding: 'utf8', shell: false });
    return r.status === 0;
}

function findPython() {
    // 1) Common command names
    for (const cmd of process.platform === 'win32' ? ['py', 'python', 'python3'] : ['python3', 'python']) {
        try {
            const r = spawnSync(cmd, ['--version'], { encoding: 'utf8', shell: true });
            if (r.status === 0) return cmd;
        } catch { /* continue */ }
    }

    // 2) Explicit Windows paths (no Hermes required — just common installs)
    const home = os.homedir();
    const candidates = [
        path.join(home, 'AppData', 'Local', 'Programs', 'Python', 'Python312', 'python.exe'),
        path.join(home, 'AppData', 'Local', 'Programs', 'Python', 'Python311', 'python.exe'),
        path.join(home, 'AppData', 'Local', 'Programs', 'Python', 'Python313', 'python.exe'),
        path.join(home, 'AppData', 'Local', 'Microsoft', 'WindowsApps', 'python.exe'),
        path.join(home, 'AppData', 'Local', 'hermes', 'hermes-agent', 'venv', 'Scripts', 'python.exe'),
        path.join(home, 'AppData', 'Local', 'uv', 'python', 'python.exe'),
        'C:\\\\Python312\\\\python.exe',
        'C:\\\\Python311\\\\python.exe',
    ];
    for (const p of candidates) {
        if (exists(p)) return p;
    }
    return null;
}

function runPythonCli() {
    const py = findPython();
    if (!py) {
        console.error('❌ Python not found.');
        console.error('Install Python 3.11+ from https://www.python.org/downloads/');
        console.error('During install, check: "Add python.exe to PATH"');
        process.exit(1);
    }
    const r = spawnSync(py, [cliPath, ...args], { stdio: 'inherit', shell: false });
    process.exit(r.status || 0);
}

function runInstall() {
    console.log('🚀 Installing SAO Dependencies...');
    console.log('   (Hermes will be installed here — you do NOT need Hermes beforehand)\n');
    const installScript = path.join(SAO_DIR, 'scripts', 'install.ps1');
    if (!exists(installScript)) {
        console.error('❌ install.ps1 not found at', installScript);
        process.exit(1);
    }
    // install.ps1 is PowerShell-only — no Python needed
    const r = spawnSync(
        'powershell.exe',
        ['-ExecutionPolicy', 'Bypass', '-File', installScript],
        { stdio: 'inherit', shell: false }
    );
    process.exit(r.status || 0);
}

switch (command) {
    case 'install':
        runInstall();
        break;
    case 'start':
    case 'status':
    case 'stop':
    case 'create':
    case 'setup':
        runPythonCli();
        break;
    default:
        console.log(`
SAO - Sira Agentic Orchestrator

Usage:
  sao install        # Install deps (Hermes, 9Router, Graphify, Claude Code)
  sao create vault   # Generate new Obsidian Vault with Sira structure
  sao setup vault    # Link existing Vault (paste path)
  sao start          # Launch SAO services
  sao status         # Check running services
  sao stop           # Stop all services

Notes:
  - sao install does NOT require Hermes beforehand (it installs Hermes)
  - Python 3.11+ is required for CLI commands (create/setup/start/status/stop)
  - Install from GitHub: npm install -g git+https://github.com/gilangprtm/sao.git
`);
}
