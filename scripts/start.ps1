# scripts/start.ps1
# SAO start: vault bind -> graph update -> Hermes owns Graphify MCP (stdio) -> subconscious cron -> Hermes core
# ASCII-only comments (PowerShell on Windows may mis-parse UTF-8 em dashes as mojibake)
param(
    [switch]$CleanGraph
)

$ErrorActionPreference = "Stop"

$baseDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $baseDir

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Starting SAO (Sira Agentic Orchestrator)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Version: package start.ps1 (ASCII-safe)" -ForegroundColor DarkGray

$hasLocalHermes = Test-Path (Join-Path $baseDir "services\hermes")
$hasLocalGraphify = Test-Path (Join-Path $baseDir "services\graphify")
if (-Not $hasLocalHermes) {
    Write-Host "   Note: services\hermes not under SAO package (optional if Hermes already global)." -ForegroundColor DarkGray
}
if (-Not $hasLocalGraphify) {
    Write-Host "   Note: services\graphify missing - graph update/MCP will use system python -m graphify if available." -ForegroundColor DarkGray
}

# 1. Read Vault Path from Config
$saoConfigPath = Join-Path $env:USERPROFILE ".sao\config.json"
$vaultPath = ""

if (Test-Path $saoConfigPath) {
    try {
        $config = Get-Content -Path $saoConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $vaultPath = $config.vault_path
    } catch {
        Write-Host "   Config read error: $_" -ForegroundColor Yellow
    }
}

if (-Not $vaultPath -Or -Not (Test-Path $vaultPath)) {
    Write-Host "   Vault path not set or invalid. Run 'sao setup vault' before starting." -ForegroundColor Red
    Write-Host "   Aborting." -ForegroundColor Red
    exit 1
}

# 1b. Resolve Hermes state.db
$stateDbCandidates = @(
    (Join-Path $env:LOCALAPPDATA "hermes\state.db"),
    (Join-Path $env:USERPROFILE ".hermes\state.db")
)
$hermesStateDb = $null
foreach ($c in $stateDbCandidates) {
    if ($c -and (Test-Path $c)) {
        $hermesStateDb = $c
        break
    }
}
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
            if ($hit) {
                $hermesStateDb = $hit.FullName
                break
            }
        }
    }
}

$env:SAO_VAULT_PATH = $vaultPath
$env:SAO_HOME = Join-Path $env:USERPROFILE ".sao"
if ($hermesStateDb) {
    $env:HERMES_STATE_DB = $hermesStateDb
    $env:SAO_HERMES_STATE_DB = $hermesStateDb
    Write-Host "--> Hermes state.db: $hermesStateDb" -ForegroundColor Green
} else {
    Write-Host "--> Hermes state.db: not found yet (appears after first Hermes run)" -ForegroundColor Yellow
}
Write-Host "--> SAO_VAULT_PATH=$vaultPath" -ForegroundColor Green

# 2. Graphify python + index update
$graphifyPython = Join-Path $baseDir "services\graphify\.venv\Scripts\python.exe"
if (-Not (Test-Path $graphifyPython)) {
    $graphifyPython = "python"
}
$graphifyWorkDir = Join-Path $baseDir "services\graphify"
if (-Not (Test-Path $graphifyWorkDir)) {
    $graphifyWorkDir = $baseDir
}

$graphifyOut = Join-Path $vaultPath "graphify-out"

function Invoke-GraphifyUpdate {
    param([string[]]$ExtraArgs)
    $argList = @("-m", "graphify", "update", $vaultPath) + $ExtraArgs
    try {
        if (Test-Path (Join-Path $baseDir "services\graphify\.venv\Scripts\python.exe")) {
            & $graphifyPython @argList
        } else {
            & python -m graphify update $vaultPath @ExtraArgs 2>$null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "    Graphify update skipped or failed. Continuing..." -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "    Graphify update skipped or failed. Continuing..." -ForegroundColor Yellow
    }
}

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
    Invoke-GraphifyUpdate -ExtraArgs @("--force")
} else {
    Write-Host "--> Updating Vault Graph Index (Incremental)..." -ForegroundColor Yellow
    Invoke-GraphifyUpdate -ExtraArgs @()
}

# 3. Sync Graphify MCP into Hermes config (stdio - Hermes owns lifecycle)
function Get-HermesConfigPath {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "hermes\config.yaml"),
        (Join-Path $env:USERPROFILE ".hermes\config.yaml")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    # Create default under LOCALAPPDATA
    $dir = Join-Path $env:LOCALAPPDATA "hermes"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $path = Join-Path $dir "config.yaml"
    if (-Not (Test-Path $path)) {
        Set-Content -Path $path -Value "# Hermes config (created by SAO start)`n" -Encoding UTF8
    }
    return $path
}

function Set-SaoGraphifyMcp {
    param(
        [string]$ConfigPath,
        [string]$Py,
        [string]$Vault
    )
    if (-Not (Test-Path $ConfigPath)) { return }

    $raw = Get-Content -Path $ConfigPath -Raw -Encoding UTF8
    if ($null -eq $raw) { $raw = "" }

    $vaultNorm = $Vault -replace '\\', '/'
    $pyNorm = $Py -replace '\\', '/'

    # Remove previous SAO-managed graphify blocks (simple line scrub)
    $lines = $raw -split "`r?`n"
    $out = New-Object System.Collections.Generic.List[string]
    $skip = $false
    $depth = 0
    foreach ($line in $lines) {
        if ($line -match '^\s*graphify\s*:') {
            $skip = $true
            $depth = 0
            continue
        }
        if ($skip) {
            if ($line -match '^\S' -and $line -notmatch '^\s') {
                $skip = $false
            } elseif ($line -match '^\s+\S' -or $line -match '^\s*$') {
                continue
            } else {
                $skip = $false
            }
        }
        if (-Not $skip) {
            [void]$out.Add($line)
        }
    }
    $raw = ($out -join "`n")

    $block = @"

# SAO-managed Graphify MCP (stdio - Hermes owns lifecycle)
mcp_servers:
  graphify:
    command: $pyNorm
    args: ["-m", "graphify", "--mcp", "$vaultNorm"]
    enabled: true
"@

    if ($raw -match '(?m)^mcp_servers\s*:') {
        # Insert graphify under existing mcp_servers
        $insert = @"
  graphify:
    command: $pyNorm
    args: ["-m", "graphify", "--mcp", "$vaultNorm"]
    enabled: true
"@
        # If graphify already removed above, append after mcp_servers:
        $raw = [regex]::Replace($raw, '(?m)^(mcp_servers\s*:\s*\r?\n)', "`$1$insert")
    } else {
        $raw = $raw.TrimEnd() + "`n" + $block + "`n"
    }

    Set-Content -Path $ConfigPath -Value $raw -Encoding UTF8
}

$hermesConfig = Get-HermesConfigPath
$graphifyPyForMcp = $graphifyPython
if ($graphifyPython -eq "python") {
    try {
        $which = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($which) { $graphifyPyForMcp = $which }
    } catch { }
}
$vaultForMcp = ($vaultPath -replace '\\', '/')

try {
    Set-SaoGraphifyMcp -ConfigPath $hermesConfig -Py $graphifyPyForMcp -Vault $vaultForMcp
    $other = Join-Path $env:USERPROFILE ".hermes\config.yaml"
    if ((Test-Path $other) -and ($other -ne $hermesConfig)) {
        Set-SaoGraphifyMcp -ConfigPath $other -Py $graphifyPyForMcp -Vault $vaultForMcp
    }
    Write-Host "--> Graphify MCP (stdio) registered in Hermes config: $hermesConfig" -ForegroundColor Green
} catch {
    Write-Host "   Hermes MCP config sync skipped: $_" -ForegroundColor DarkGray
}

# 4. Copy subconscious script + optional cron
$hermesPython = Join-Path $baseDir "services\hermes\.venv\Scripts\python.exe"
if (-Not (Test-Path $hermesPython)) {
    $globalHermes = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\venv\Scripts\python.exe"
    if (Test-Path $globalHermes) {
        $hermesPython = $globalHermes
    } else {
        $hermesPython = "python"
    }
}

try {
    $saoScript = Join-Path $baseDir "scripts\subconscious.py"
    $hermesScripts = Join-Path $env:LOCALAPPDATA "hermes\scripts"
    New-Item -ItemType Directory -Force -Path $hermesScripts -ErrorAction SilentlyContinue | Out-Null
    $targetScript = Join-Path $hermesScripts "sao_subconscious.py"
    if (Test-Path $saoScript) {
        Copy-Item -Path $saoScript -Destination $targetScript -Force -ErrorAction SilentlyContinue
    }

    $existingCron = & $hermesPython -m hermes_cli cron list 2>$null | Select-String "sao_subconscious"
    if (-Not $existingCron) {
        Write-Host "--> Registering Daily Subconscious Cron in Hermes..." -ForegroundColor Yellow
        & $hermesPython -m hermes_cli cron create --name "SAO Subconscious Daily" --schedule "0 9 * * *" --script "sao_subconscious.py" --no-agent --deliver local 2>$null | Out-Null
    }
} catch {
    Write-Host "   Auto-cron register skipped." -ForegroundColor DarkGray
}

# 5. Start Hermes Core
Write-Host "--> Launching Hermes Core (Port 20477)..." -ForegroundColor Yellow
Write-Host "    Graphify: managed by Hermes MCP (stdio), not a separate port." -ForegroundColor DarkGray
$env:HERMES_PORT = "20477"

$hermesWorkDir = Join-Path $baseDir "services\hermes"
$hermesPyStart = Join-Path $hermesWorkDir ".venv\Scripts\python.exe"

if (Test-Path $hermesPyStart) {
    Write-Host "    Using local services\hermes venv" -ForegroundColor DarkGray
    Start-Process -FilePath $hermesPyStart -ArgumentList "-m", "hermes_api" -WorkingDirectory $hermesWorkDir -NoNewWindow -Wait
} else {
    # Fallback: try hermes CLI on PATH / global install
    $hermesCmd = Get-Command hermes -ErrorAction SilentlyContinue
    if ($hermesCmd) {
        Write-Host "    Using global 'hermes' CLI" -ForegroundColor DarkGray
        Write-Host "    Tip: for gateway, run Hermes the way you already use on this machine." -ForegroundColor DarkGray
        try {
            & hermes 2>&1 | Out-Host
        } catch {
            Write-Host "    hermes CLI failed: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "    ERROR: services\hermes not ready and 'hermes' not on PATH." -ForegroundColor Red
        Write-Host "    Fix:" -ForegroundColor Yellow
        Write-Host "      1) Re-run: sao install" -ForegroundColor Yellow
        Write-Host "      2) Or install Hermes Agent globally, then start it yourself" -ForegroundColor Yellow
        Write-Host "      3) After Hermes runs once, state.db appears under %LOCALAPPDATA%\hermes\" -ForegroundColor Yellow
        exit 1
    }
}
