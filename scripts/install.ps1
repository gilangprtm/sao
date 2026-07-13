# scripts/install.ps1
$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Installing SAO (Sira Agentic Orchestrator)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$baseDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $baseDir

function Test-Command($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
    # uv default install locations
    $uvLocal = Join-Path $env:USERPROFILE ".local\bin"
    $uvCargo = Join-Path $env:USERPROFILE ".cargo\bin"
    if (Test-Path $uvLocal) { $env:Path = "$uvLocal;$env:Path" }
    if (Test-Path $uvCargo) { $env:Path = "$uvCargo;$env:Path" }
}

function Ensure-Uv {
    Refresh-Path
    if (Test-Command "uv") {
        Write-Host "--> uv already installed: $(uv --version)" -ForegroundColor Green
        return
    }

    Write-Host "--> uv not found. Installing uv automatically..." -ForegroundColor Yellow
    try {
        irm https://astral.sh/uv/install.ps1 | iex
    } catch {
        Write-Host "   Official installer failed, trying pip fallback..." -ForegroundColor Yellow
        if (Test-Command "python") {
            python -m pip install --user uv
        } elseif (Test-Command "py") {
            py -m pip install --user uv
        } else {
            throw "Failed to install uv. Install Python first, then re-run sao install."
        }
    }

    Refresh-Path

    if (-Not (Test-Command "uv")) {
        throw "uv installed but still not in PATH. Restart terminal and run: sao install"
    }

    Write-Host "--> uv installed: $(uv --version)" -ForegroundColor Green
}

# 0. Prerequisites bootstrap
Write-Host "`n[0/4] Checking prerequisites..." -ForegroundColor Yellow

if (-Not (Test-Command "git")) {
    throw "Git not found. Install Git first: https://git-scm.com/download/win"
}
if (-Not (Test-Command "npm")) {
    throw "Node.js/npm not found. Install Node.js 20+: https://nodejs.org"
}

Ensure-Uv

$services = @{
    "hermes"   = "https://github.com/nousresearch/hermes-agent.git"
    "9router"  = "https://github.com/decolua/9router.git"
    "graphify" = "https://github.com/Graphify-Labs/graphify.git"
}

# 1. Clone & Rebrand
Write-Host "`n[1/4] Cloning services (hard-fork)..." -ForegroundColor Yellow
foreach ($svc in $services.GetEnumerator()) {
    $name = $svc.Name
    $url = $svc.Value
    $target = "services\$name"

    if (-Not (Test-Path $target)) {
        Write-Host "--> Cloning $name..."
        git clone --depth 1 $url $target
        Remove-Item -Recurse -Force "$target\.git" -ErrorAction SilentlyContinue
    } else {
        Write-Host "--> $name already exists. Skipping."
    }
}

# 2. Install Claude Code
Write-Host "`n[2/4] Installing Claude Code Worker..." -ForegroundColor Yellow
try {
    irm https://claude.ai/install.ps1 | iex
} catch {
    Write-Host "--> Claude Code install skipped/failed: $_" -ForegroundColor Yellow
    Write-Host "    You can install later via: irm https://claude.ai/install.ps1 | iex"
}

# 3. Setup Dependencies
Write-Host "`n[3/4] Installing service dependencies..." -ForegroundColor Yellow

Write-Host "--> Setting up 9Router..."
Set-Location "services\9router"
if (Test-Path ".env.example") { Copy-Item ".env.example" ".env" -Force }
npm install
Set-Location $baseDir

Write-Host "--> Setting up Graphify..."
Set-Location "services\graphify"
uv venv
uv pip install -e .
Set-Location $baseDir

Write-Host "--> Setting up Hermes..."
Set-Location "services\hermes"
uv venv
uv pip install -e .
Set-Location $baseDir

# 4. Setup task logs
Write-Host "`n[4/4] Setting up SAO local state..." -ForegroundColor Yellow
$taskLogDir = Join-Path $env:LOCALAPPDATA "sao\tasks"
New-Item -ItemType Directory -Force -Path $taskLogDir | Out-Null

Write-Host "--> CLI is provided by npm global package (sira-agentic-orchestrator)."
Write-Host "    If 'sao' is missing, re-run: npm install -g git+https://github.com/gilangprtm/sao.git"

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "  Next steps:" -ForegroundColor Green
Write-Host "    1. sao create vault" -ForegroundColor Green
Write-Host "    2. sao start" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
