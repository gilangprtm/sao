# scripts/install.ps1
$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Installing SAO (Sira Agentic Orchestrator)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$baseDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $baseDir

$services = @{
    "hermes" = "https://github.com/nousresearch/hermes-agent.git"
    "9router" = "https://github.com/decolua/9router.git"
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
irm https://claude.ai/install.ps1 | iex

# 3. Setup Dependencies
Write-Host "`n[3/4] Installing service dependencies..." -ForegroundColor Yellow

Write-Host "--> Setting up 9Router..."
Set-Location "services\9router"
if (Test-Path ".env.example") { Copy-Item ".env.example" ".env" }
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

# 4. Setup CLI Wrapper & Task Logs
Write-Host "`n[4/4] Setting up SAO CLI..." -ForegroundColor Yellow

# Buat folder log task untuk Subconscious
$taskLogDir = Join-Path $env:LOCALAPPDATA "sao\tasks"
New-Item -ItemType Directory -Force -Path $taskLogDir | Out-Null

# Prefer npm global bin for `sao` command.
# Do NOT create a hard-coded python bat (breaks when python not in PATH).
Write-Host "--> CLI is provided by npm global package (sira-agentic-orchestrator)."
Write-Host "    If 'sao' is missing, re-run: npm install -g git+https://github.com/gilangprtm/sao.git"

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "  Restart your terminal and run 'sao start'" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green