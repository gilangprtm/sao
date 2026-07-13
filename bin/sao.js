#!/usr/bin/env node

const { spawnSync } = require('child_process');
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

function findPython() {
    for (const cmd of process.platform === 'win32' ? ['py', 'python', 'python3'] : ['python3', 'python']) {
        try {
            const r = spawnSync(cmd, ['--version'], { encoding: 'utf8', shell: true });
            if (r.status === 0) return cmd;
        } catch { /* continue */ }
    }

    const home = os.homedir();
    const candidates = [
        path.join(home, 'AppData', 'Local', 'Programs', 'Python', 'Python312', 'python.exe'),
        path.join(home, 'AppData', 'Local', 'Programs', 'Python', 'Python311', 'python.exe'),
        path.join(home, 'AppData', 'Local', 'Programs', 'Python', 'Python313', 'python.exe'),
        path.join(home, 'AppData', 'Local', 'Microsoft', 'WindowsApps', 'python.exe'),
        path.join(home, 'AppData', 'Local', 'hermes', 'hermes-agent', 'venv', 'Scripts', 'python.exe'),
        path.join(home, 'AppData', 'Local', 'uv', 'python', 'python.exe'),
        'C:\\Python312\\python.exe',
        'C:\\Python311\\python.exe',
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
    console.log('🚀 Installing SAO Core...');
    console.log('   Core only: Hermes + 9Router + Graphify');
    console.log('   Worker (Claude Code / OpenCode / etc.) is OPTIONAL\n');

    if (process.platform === 'win32') {
        const installScript = path.join(SAO_DIR, 'scripts', 'install.ps1');
        if (!exists(installScript)) {
            console.error('❌ install.ps1 not found at', installScript);
            process.exit(1);
        }
        const r = spawnSync(
            'powershell.exe',
            ['-ExecutionPolicy', 'Bypass', '-File', installScript],
            { stdio: 'inherit', shell: false }
        );
        process.exit(r.status || 0);
    } else {
        const installSh = path.join(SAO_DIR, 'scripts', 'install.sh');
        if (exists(installSh)) {
            const r = spawnSync('bash', [installSh], { stdio: 'inherit', shell: false });
            process.exit(r.status || 0);
        }
        console.error('❌ Linux/macOS installer (install.sh) not ready yet.');
        console.error('   For now use Windows, or install services manually.');
        process.exit(1);
    }
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
    case 'set':
        runPythonCli();
        break;
    default:
        console.log(`
SAO - Sira Agentic Orchestrator

Usage:
  sao install            # Install core: Hermes + 9Router + Graphify (+ auto uv)
  sao create vault       # Generate Markdown vault with Sira structure
  sao setup vault        # Link existing vault folder
  sao set worker [cmd]   # Set coding worker (default: sira)
  sao start              # Launch SAO services
  sao status             # Check services + vault + worker
  sao stop               # Stop all services

Worker examples:
  sao set worker sira        # Hermes itself (no external CLI)
  sao set worker claude      # Claude Code CLI
  sao set worker opencode    # OpenCode CLI
  sao set worker <any-cmd>   # any binary on PATH

Notes:
  - Worker is OPTIONAL. Core install never requires Claude Code.
  - Python 3.11+ required for CLI commands
  - Install: npm install -g git+https://github.com/gilangprtm/sao.git
`);
}
