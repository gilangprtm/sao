#!/usr/bin/env node

const { execSync } = require('child_process');
const path = require('path');
const os = require('os');

const args = process.argv.slice(2);
const command = args[0] || 'help';

// SAO install dir is wherever this package is installed globally
const SAO_DIR = path.resolve(__dirname, '..');

// Python CLI entry point
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
        console.log("🚀 Installing SAO Dependencies...");
        const installScript = path.join(SAO_DIR, 'scripts', 'install.ps1');
        execSync(`powershell.exe -ExecutionPolicy Bypass -File "${installScript}"`, { stdio: 'inherit' });
        break;
    case 'start':
    case 'status':
    case 'stop':
        runPythonCli();
        break;
    default:
        console.log(`
SAO - Sira Agentic Orchestrator

Usage:
  sao install   # Install dependencies (Hermes, 9Router, Graphify)
  sao start     # Launch SAO services
  sao status    # Check running services
  sao stop      # Stop all services
        `);
}
