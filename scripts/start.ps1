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

    $existingCron = & $hermesPython -m hermes_cli.main cron list 2>$null | Select-String "sao_subconscious"
    if (-Not $existingCron) {
        Write-Host "--> Registering Daily Subconscious Cron in Hermes..." -ForegroundColor Yellow
        & $hermesPython -m hermes_cli.main cron create --name "SAO Subconscious Daily" --schedule "0 9 * * *" --script "sao_subconscious.py" --no-agent --deliver local 2>$null | Out-Null
    }
} catch {
    Write-Host "   Auto-cron register skipped." -ForegroundColor DarkGray
}

# 5. Start Hermes (real CLI: hermes / hermes_cli.main - NOT hermes_api)
#    Entry points from hermes-agent pyproject:
#      hermes = hermes_cli.main:main
#      hermes-agent = run_agent:main
#    Useful subcommands: setup | chat | gateway run | serve | status | doctor
Write-Host "--> Launching Hermes..." -ForegroundColor Yellow
Write-Host "    Graphify: managed by Hermes MCP (stdio), not a separate port." -ForegroundColor DarkGray

$hermesWorkDir = Join-Path $baseDir "services\hermes"
$hermesExe = Join-Path $hermesWorkDir ".venv\Scripts\hermes.exe"
$hermesPy = Join-Path $hermesWorkDir ".venv\Scripts\python.exe"

function Resolve-HermesCommand {
    if (Test-Path $hermesExe) {
        return @{ Kind = "exe"; Path = $hermesExe; WorkDir = $hermesWorkDir }
    }
    if (Test-Path $hermesPy) {
        return @{ Kind = "py"; Path = $hermesPy; WorkDir = $hermesWorkDir }
    }
    $globalExe = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\venv\Scripts\hermes.exe"
    if (Test-Path $globalExe) {
        return @{ Kind = "exe"; Path = $globalExe; WorkDir = (Split-Path (Split-Path $globalExe)) }
    }
    $onPath = Get-Command hermes -ErrorAction SilentlyContinue
    if ($onPath) {
        return @{ Kind = "exe"; Path = $onPath.Source; WorkDir = $baseDir }
    }
    return $null
}

function Invoke-Hermes {
    param(
        [hashtable]$Cmd,
        [string[]]$HermesArgs
    )
    if ($Cmd.Kind -eq "exe") {
        & $Cmd.Path @HermesArgs
        return $LASTEXITCODE
    }
    # python -m hermes_cli.main ...
    & $Cmd.Path -m hermes_cli.main @HermesArgs
    return $LASTEXITCODE
}

$hermesCmd = Resolve-HermesCommand
if (-Not $hermesCmd) {
    Write-Host "    ERROR: Hermes CLI not found." -ForegroundColor Red
    Write-Host "    Fix:" -ForegroundColor Yellow
    Write-Host "      1) Re-run: sao install" -ForegroundColor Yellow
    Write-Host "      2) Confirm: dir services\hermes\.venv\Scripts\hermes.exe" -ForegroundColor Yellow
    exit 1
}

Write-Host "    Using: $($hermesCmd.Path)" -ForegroundColor DarkGray

# First-run: if no model/config usable, guide setup
$configProbe = Join-Path $env:LOCALAPPDATA "hermes\config.yaml"
$needsSetup = $false
if (-Not (Test-Path $configProbe)) {
    $needsSetup = $true
} else {
    try {
        $cfgText = Get-Content $configProbe -Raw -ErrorAction SilentlyContinue
        # empty or only SAO-created stub
        if (-Not $cfgText -or $cfgText.Length -lt 40) { $needsSetup = $true }
    } catch { $needsSetup = $true }
}

if ($needsSetup) {
    Write-Host ""
    Write-Host "    Hermes needs first-time setup (model/provider)." -ForegroundColor Yellow
    Write-Host "    Running: hermes setup" -ForegroundColor Cyan
    Write-Host "    (interactive - pick model / API key)" -ForegroundColor DarkGray
    Write-Host ""
    Push-Location $hermesCmd.WorkDir
    try {
        $code = Invoke-Hermes -Cmd $hermesCmd -HermesArgs @("setup")
    } finally {
        Pop-Location
    }
    if ($code -ne 0) {
        Write-Host "    setup exited with code $code" -ForegroundColor Yellow
        Write-Host "    Manual: `"$($hermesCmd.Path)`" setup" -ForegroundColor Yellow
    }
}

# Prefer gateway if messaging already configured; else open chat (creates state.db)
Write-Host ""
Write-Host "    Starting Hermes gateway (foreground)." -ForegroundColor Cyan
Write-Host "    - Discord/Telegram/etc. if configured" -ForegroundColor DarkGray
Write-Host "    - Ctrl+C to stop" -ForegroundColor DarkGray
Write-Host "    - First successful run creates state.db under %LOCALAPPDATA%\hermes\" -ForegroundColor DarkGray
Write-Host "    Alt (CLI chat only): `"$($hermesCmd.Path)`" chat" -ForegroundColor DarkGray
Write-Host ""

Push-Location $hermesCmd.WorkDir
try {
    # gateway run = foreground messaging bus (creates sessions -> state.db)
    $code = Invoke-Hermes -Cmd $hermesCmd -HermesArgs @("gateway", "run")
    if ($code -ne 0) {
        Write-Host "    gateway run failed (exit $code). Falling back to: hermes chat" -ForegroundColor Yellow
        Invoke-Hermes -Cmd $hermesCmd -HermesArgs @("chat")
    }
} finally {
    Pop-Location
}
