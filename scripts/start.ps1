# scripts/start.ps1
# SAO start: vault bind → graph update → Hermes owns Graphify MCP (stdio) → subconscious cron → Hermes core
param(
    [switch]$CleanGraph
)

$ErrorActionPreference = "Stop"

$baseDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $baseDir

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Starting SAO (Sira Agentic Orchestrator)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check if services exist (local clone under SAO). Global Hermes still works for MCP/env bind.
$hasLocalHermes = Test-Path "services\hermes"
$hasLocalGraphify = Test-Path "services\graphify"
if (-Not $hasLocalHermes) {
    Write-Host "   Note: services\hermes not under SAO package (optional if Hermes already global)." -ForegroundColor DarkGray
}
if (-Not $hasLocalGraphify) {
    Write-Host "   Note: services\graphify missing — graph update/MCP will use system 'python -m graphify' if available." -ForegroundColor DarkGray
}

# 1. Read Vault Path from Config
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

# 1b. Resolve Hermes state.db (for subconscious + env)
$stateDbCandidates = @(
    (Join-Path $env:LOCALAPPDATA "hermes\state.db"),
    (Join-Path $env:USERPROFILE ".hermes\state.db"),
    (Join-Path $env:USERPROFILE "AppData\Local\hermes\state.db")
)
$hermesStateDb = $null
foreach ($c in $stateDbCandidates) {
    if (Test-Path $c) { $hermesStateDb = $c; break }
}
# Prefer newest if multiple profiles later
if (-Not $hermesStateDb) {
    $searchRoots = @(
        (Join-Path $env:LOCALAPPDATA "hermes"),
        (Join-Path $env:USERPROFILE ".hermes")
    )
    foreach ($root in $searchRoots) {
        if (Test-Path $root) {
            $hit = Get-ChildItem -Path $root -Filter "state.db" -Recurse -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending |
                Select-Object -First 1
            if ($hit) { $hermesStateDb = $hit.FullName; break }
        }
    }
}

# Export env for Hermes, workers, subconscious children
$env:SAO_VAULT_PATH = $vaultPath
$env:SAO_HOME = Join-Path $env:USERPROFILE ".sao"
if ($hermesStateDb) {
    $env:HERMES_STATE_DB = $hermesStateDb
    $env:SAO_HERMES_STATE_DB = $hermesStateDb
    Write-Host "--> Hermes state.db: $hermesStateDb" -ForegroundColor Green
} else {
    Write-Host "--> Hermes state.db: not found yet (will appear after first Hermes run)" -ForegroundColor Yellow
}
Write-Host "--> SAO_VAULT_PATH=$vaultPath" -ForegroundColor Green

# 2. Update Graphify Index (files only — MCP process owned by Hermes)
$graphifyPython = Join-Path $baseDir "services\graphify\.venv\Scripts\python.exe"
if (-Not (Test-Path $graphifyPython)) {
    $graphifyPython = "python"
}
$graphifyPython = (Resolve-Path $graphifyPython -ErrorAction SilentlyContinue)
if (-Not $graphifyPython) { $graphifyPython = "python" } else { $graphifyPython = $graphifyPython.Path }

$graphifyOut = Join-Path $vaultPath "graphify-out"

if ($CleanGraph) {
    Write-Host "--> Clean graph rebuild (full)..." -ForegroundColor Yellow
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
        Start-Process -FilePath $graphifyPython `
            -ArgumentList "-m", "graphify", "update", $vaultPath, "--force" `
            -WorkingDirectory "services\graphify" -NoNewWindow -Wait
    } catch {
        Write-Host "    Clean graph rebuild failed. Continuing..." -ForegroundColor Yellow
    }
} else {
    Write-Host "--> Updating Vault Graph Index (Incremental)..." -ForegroundColor Yellow
    try {
        Start-Process -FilePath $graphifyPython `
            -ArgumentList "-m", "graphify", "update", $vaultPath `
            -WorkingDirectory "services\graphify" -NoNewWindow -Wait
    } catch {
        Write-Host "    Graphify update skipped or failed. Continuing..." -ForegroundColor Yellow
    }
}

# 3. NO separate Graphify HTTP process (port 20476).
#    Hermes launches Graphify as stdio MCP from mcp_servers — auto restart with Hermes.

# 4. Sync Hermes config: vault pointer + mcp_servers.graphify (stdio)
$hermesConfigDir = Join-Path $env:LOCALAPPDATA "hermes"
if (-Not (Test-Path $hermesConfigDir)) {
    $hermesConfigDir = Join-Path $env:USERPROFILE ".hermes"
}
New-Item -ItemType Directory -Force -Path $hermesConfigDir -ErrorAction SilentlyContinue | Out-Null
$vaultPathYaml = $vaultPath -replace '\\', '/'
$stateDbYaml = if ($hermesStateDb) { ($hermesStateDb -replace '\\', '/') } else { "" }

# Pointer files (also written by cli.py bind_vault; keep in sync here)
$pointer = @{
    vault_path        = $vaultPath
    vault_path_posix  = $vaultPathYaml
    hermes_state_db   = $hermesStateDb
    updated_at        = (Get-Date -Format "o")
} | ConvertTo-Json
Set-Content -Path (Join-Path $hermesConfigDir "sao_vault_path.txt") -Value $vaultPathYaml -Encoding UTF8
Set-Content -Path (Join-Path $hermesConfigDir "sao_vault.json") -Value $pointer -Encoding UTF8
$homeHermes = Join-Path $env:USERPROFILE ".hermes"
if (Test-Path $homeHermes) {
    Set-Content -Path (Join-Path $homeHermes "sao_vault_path.txt") -Value $vaultPathYaml -Encoding UTF8
    Set-Content -Path (Join-Path $homeHermes "sao_vault.json") -Value $pointer -Encoding UTF8
}

# Prefer venv python absolute path for MCP (resilient)
$graphifyPyForMcp = $graphifyPython -replace '\\', '/'
$vaultForMcp = $vaultPathYaml

$hermesConfig = Join-Path $hermesConfigDir "config.yaml"
# Also try USERPROFILE .hermes
if (-Not (Test-Path $hermesConfig)) {
    $alt = Join-Path $env:USERPROFILE ".hermes\config.yaml"
    if (Test-Path $alt) { $hermesConfig = $alt }
}

function Set-SaoGraphifyMcp {
    param([string]$ConfigPath, [string]$Py, [string]$Vault)
    if (-Not (Test-Path $ConfigPath)) {
        $block = @"
# SAO-managed Graphify MCP (stdio — Hermes owns lifecycle)
mcp_servers:
  graphify:
    command: $Py
    args: ["-m", "graphify", "--mcp", "$Vault"]
    enabled: true
"@
        Set-Content -Path $ConfigPath -Value $block -Encoding UTF8
        return
    }
    $raw = Get-Content -Path $ConfigPath -Raw -ErrorAction SilentlyContinue
    if ($null -eq $raw) { $raw = "" }

    # If graphify already under mcp_servers, rewrite command/args block for graphify only
    if ($raw -match "(?m)^\s*graphify\s*:") {
        # Replace command line under graphify
        $raw = [regex]::Replace(
            $raw,
            '(?ms)(graphify\s*:\s*\r?\n(?:[ \t]+[^\r\n]*\r?\n)*?)',
            {
                param($m)
@"
graphify:
    command: $Py
    args: ["-m", "graphify", "--mcp", "$Vault"]
    enabled: true

"@
            }
        )
        # Fallback simple path replace on old style command: ["python", "-m", "graphify", ...]
        $raw = [regex]::Replace(
            $raw,
            '(?m)(command:\s*\[.*"graphify".*)"([^"]+)"(\s*\])',
            { param($m) $m.Groups[1].Value + "`"$Vault`"" + $m.Groups[3].Value }
        )
        Set-Content -Path $ConfigPath -Value $raw -Encoding UTF8
    } elseif ($raw -match "(?m)^mcp_servers\s*:") {
        $append = @"

  graphify:
    command: $Py
    args: ["-m", "graphify", "--mcp", "$Vault"]
    enabled: true
"@
        # Insert after mcp_servers:
        $raw = [regex]::Replace($raw, '(?m)^(mcp_servers\s*:\s*\r?\n)', "`$1$append")
        Set-Content -Path $ConfigPath -Value $raw -Encoding UTF8
    } else {
        $append = @"

# SAO-managed Graphify MCP (stdio — Hermes owns lifecycle)
mcp_servers:
  graphify:
    command: $Py
    args: ["-m", "graphify", "--mcp", "$Vault"]
    enabled: true
"@
        Add-Content -Path $ConfigPath -Value $append -Encoding UTF8
    }
}

try {
    Set-SaoGraphifyMcp -ConfigPath $hermesConfig -Py $graphifyPyForMcp -Vault $vaultForMcp
    # Dual-write if both hermes dirs exist
    $other = Join-Path $env:USERPROFILE ".hermes\config.yaml"
    if ((Test-Path $other) -and ($other -ne $hermesConfig)) {
        Set-SaoGraphifyMcp -ConfigPath $other -Py $graphifyPyForMcp -Vault $vaultForMcp
    }
    Write-Host "--> Graphify MCP (stdio) registered in Hermes config for: $vaultForMcp" -ForegroundColor Green
} catch {
    Write-Host "   Hermes MCP config sync skipped: $_" -ForegroundColor DarkGray
}

# 4.5 Register Subconscious Cron in Hermes if missing
$hermesPython = Join-Path $baseDir "services\hermes\.venv\Scripts\python.exe"
if (-Not (Test-Path $hermesPython)) {
    $hermesPython = "python"
}
try {
    $saoScript = Join-Path $baseDir "scripts\subconscious.py"
    $hermesScripts = Join-Path $env:LOCALAPPDATA "hermes\scripts"
    New-Item -ItemType Directory -Force -Path $hermesScripts -ErrorAction SilentlyContinue | Out-Null
    $targetScript = Join-Path $hermesScripts "sao_subconscious.py"
    Copy-Item -Path $saoScript -Destination $targetScript -Force -ErrorAction SilentlyContinue

    $existingCron = & $hermesPython -m hermes_cli cron list 2>$null | Select-String "sao_subconscious"
    if (-Not $existingCron) {
        Write-Host "--> Registering Daily Subconscious Cron in Hermes..." -ForegroundColor Yellow
        & $hermesPython -m hermes_cli cron create --name "SAO Subconscious Daily" --schedule "0 9 * * *" --script "sao_subconscious.py" --no-agent --deliver local | Out-Null
    }
} catch {
    Write-Host "   Auto-cron register skipped." -ForegroundColor DarkGray
}

# 5. Start Hermes (The Brain) — owns Graphify MCP lifecycle via stdio
Write-Host "--> Launching Hermes Core (Port 20477)..." -ForegroundColor Yellow
Write-Host "    Graphify: managed by Hermes MCP (stdio), not a separate port." -ForegroundColor DarkGray
$env:HERMES_PORT = "20477"
$hermesPython = Join-Path $baseDir "services\hermes\.venv\Scripts\python.exe"
if (-Not (Test-Path $hermesPython)) {
    $hermesPython = "python"
}
Start-Process -FilePath $hermesPython -ArgumentList "-m", "hermes_api" -WorkingDirectory "services\hermes" -NoNewWindow -Wait

Write-Host "`nSAO closed." -ForegroundColor Green
