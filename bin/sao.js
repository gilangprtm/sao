#!/usr/bin/env node

const { execSync } = require('child_process');
const path = require('path');

const args = process.argv.slice(2);
const command = args[0] || 'help';

// SAO install dir is wherever this package is installed globally
const SAO_DIR = path.resolve(__dirname, '..');
const cliPath = path.join(SAO_DIR, 'cli.py');

function runPythonCli() {
    try {
        execSync(`python "${cliPath}" ${args.join(' ')}`, { stdio: 'inherit' });
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
