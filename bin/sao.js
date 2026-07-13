#!/usr/bin/env node

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const args = process.argv.slice(2);
const command = args[0] || 'help';

const SAO_DIR = path.resolve(__dirname, '..');
const cliPath = path.join(SAO_DIR, 'cli.py');

// Find Python executable (Windows-friendly)
function findPython() {
    const candidates = [
        'python',
        'py',
        'python3',
        // Common Hermes/Ryder locations
        path.join(os.homedir(), 'AppData', 'Local', 'hermes', 'hermes-agent', 'venv', 'Scripts', 'python.exe'),
        path.join(os.homedir(), 'AppData', 'Local', 'ryder', 'venv', 'Scripts', 'python.exe'),
        path.join(os.homedir(), '.local', 'bin', 'python')
    ];

    // First try direct command
    for (const cmd of ['python', 'py', 'python3']) {
        try {
            execSync(`${cmd} --version`, { stdio: 'ignore' });
            return cmd;
        } catch { continue; }
    }

    // Fallback: find any python.exe in PATH or common locations
    for (const p of candidates) {
        if (fs.existsSync(p)) {
            try {
                execSync(`"${p}" --version`, { stdio: 'ignore' });
                return `"${p}"`;
            } catch { continue; }
        }
    }

    return null;
}

function runPythonCli() {
    const py = findPython();
    if (!py) {
        console.error('❌ Python not found. Install Python 3.11+ from https://python.org and ensure it\'s in PATH.');
        process.exit(1);
    }
    try {
        execSync(`${py} "${cliPath}" ${args.join(' ')}`, { stdio: 'inherit' });
    } catch (e) {
        process.exit(1);
    }
}

switch (command) {
    case 'install':
        console.log('🚀 Installing SAO Dependencies...');
        const installScript = path.join(SAO_DIR, 'scripts', 'install.ps1');
        try {
            execSync(`powershell.exe -ExecutionPolicy Bypass -File "${installScript}"`, { stdio: 'inherit' });
        } catch (e) {
            process.exit(1);
        }
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
  sao install        # Install dependencies (Hermes, 9Router, Graphify)
  sao create vault   # Generate new Obsidian Vault with Sira structure
  sao setup vault    # Link existing Vault (paste path)
  sao start          # Launch SAO services
  sao status         # Check running services
  sao stop           # Stop all services
        `);
}
