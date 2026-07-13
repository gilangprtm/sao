# scripts/start.ps1
param(
    [switch]$CleanGraph
)

$ErrorActionPreference = "Stop"

$baseDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $baseDir

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Starting SAO (Sira Agentic Orchestrator)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check if services exist
if (-Not (Test-Path "services\9router") -Or -Not (Test-Path "services\hermes")) {
    Write-Error "Services not installed. Run sao install first."
}

# 1. Start 9Router Gateway
Write-Host "--> Launching 9Router (Port 20475)..." -ForegroundColor Yellow
$env:NINE_ROUTER_PORT = "20475"
Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory "services\9router" -NoNewWindow

# Wait for 9Router
Start-Sleep -Seconds 5

# 2. Read Vault Path from Config
$saoConfigPath = Join-Path $env:USERPROFILE ".sao\config.json"
$vaultPath = ""

if (Test-Path $saoConfigPath) {
    try {
        $config = Get-Content -Path $saoConfigPath -Raw | ConvertFrom-Json
        $vaultPath = $config.vault_path
    } catch {
        Write-Host "   Config read error. Using default." -ForegroundColor Yellow
    }
}

if (-Not $vaultPath -Or -Not (Test-Path $vaultPath)) {
    Write-Host "   Vault path not set or invalid. Run 'sao setup vault' before starting." -ForegroundColor Red
    Write-Host "   Aborting." -ForegroundColor Red
    exit 1
}

# 2.5 Update Graphify Index
$graphifyPython = Join-Path $baseDir "services\graphify\.venv\Scripts\python.exe"
if (-Not (Test-Path $graphifyPython)) {
    $graphifyPython = "python"
}

$graphifyOut = Join-Path $vaultPath "graphify-out"

if ($CleanGraph) {
    Write-Host "--> Clean graph rebuild (full)..." -ForegroundColor Yellow
    Write-Host "    This removes stale nodes (deleted vault files) and rebuilds index." -ForegroundColor Yellow
    Write-Host "    First run / large vault can take 1-3+ minutes." -ForegroundColor Yellow

    # Wipe previous graph artifacts so deleted files cannot leave ghost nodes
    if (Test-Path $graphifyOut) {
        try {
            Get-ChildItem -Path $graphifyOut -Force -ErrorAction SilentlyContinue |
                Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "    Cleared: $graphifyOut" -ForegroundColor DarkYellow
        } catch {
            Write-Host "    Could not fully clear graphify-out: $_" -ForegroundColor Yellow
        }
    }
    New-Item -ItemType Directory -Force -Path $graphifyOut | Out-Null

    try {
        # --force: overwrite even if rebuild has fewer nodes (handles deletions)
        Start-Process -FilePath $graphifyPython `
            -ArgumentList "-m", "graphify", "update", $vaultPath, "--force" `
            -WorkingDirectory "services\graphify" -NoNewWindow -Wait
    } catch {
        Write-Host "    Clean graph rebuild failed. Continuing with MCP..." -ForegroundColor Yellow
    }
} else {
    Write-Host "--> Updating Vault Graph Index (Incremental)..." -ForegroundColor Yellow
    Write-Host "    Only changed files re-indexed (usually seconds)." -ForegroundColor DarkGray
    try {
        Start-Process -FilePath $graphifyPython `
            -ArgumentList "-m", "graphify", "update", $vaultPath `
            -WorkingDirectory "services\graphify" -NoNewWindow -Wait
    } catch {
        Write-Host "    Graphify update skipped or failed. Continuing..." -ForegroundColor Yellow
    }
}

# 3. Start Graphify MCP Server (Port 20476)
Write-Host "--> Launching Graphify MCP (Port 20476) — serving $vaultPath ..." -ForegroundColor Yellow
Start-Process -FilePath $graphifyPython -ArgumentList "-m", "graphify", $vaultPath, "--mcp", "--port", "20476" -WorkingDirectory "services\graphify" -NoNewWindow

# Wait for Graphify
Start-Sleep -Seconds 3

# 4. Inject Sira Environment Configs
$env:ANTHROPIC_BASE_URL = "http://localhost:20475/v1"
$env:ANTHROPIC_DEFAULT_OPUS_MODEL = "fusion"
$env:ANTHROPIC_DEFAULT_SONNET_MODEL = "fusion"
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = "fusion"
$env:CLAUDE_CODE_SUBAGENT_MODEL = "fusion"

# 5. Start Hermes (The Brain)
Write-Host "--> Launching Hermes Core (Port 20477)..." -ForegroundColor Yellow
$env:HERMES_PORT = "20477"
$hermesPython = Join-Path $baseDir "services\hermes\.venv\Scripts\python.exe"
if (-Not (Test-Path $hermesPython)) {
    $hermesPython = "python"
}
Start-Process -FilePath $hermesPython -ArgumentList "-m", "hermes_api" -WorkingDirectory "services\hermes" -NoNewWindow -Wait

Write-Host "`nSAO closed." -ForegroundColor Green
