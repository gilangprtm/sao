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

# 4. Copy subconscious script + register cron (auto memory sync)
# Hermes cron CLI: hermes cron create <schedule> [--name] [--script] [--no-agent] [--deliver]
# Script path is relative to ~/.hermes/scripts/ (or %LOCALAPPDATA%\hermes\scripts on Windows)
$hermesWorkDir = Join-Path $baseDir "services\hermes"
$hermesExeForCron = Join-Path $hermesWorkDir ".venv\Scripts\hermes.exe"
if (-Not (Test-Path $hermesExeForCron)) {
    $hermesExeForCron = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\venv\Scripts\hermes.exe"
}
$hermesPython = Join-Path $hermesWorkDir ".venv\Scripts\python.exe"
if (-Not (Test-Path $hermesPython)) {
    $globalHermes = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\venv\Scripts\python.exe"
    if (Test-Path $globalHermes) {
        $hermesPython = $globalHermes
    } else {
        $hermesPython = "python"
    }
}

function Invoke-HermesCron {
    param([string[]]$CronArgs)
    if (Test-Path $hermesExeForCron) {
        & $hermesExeForCron @CronArgs
        return $LASTEXITCODE
    }
    & $hermesPython -m hermes_cli.main @CronArgs
    return $LASTEXITCODE
}

try {
    $saoScript = Join-Path $baseDir "scripts\subconscious.py"
    $scriptDirs = @(
        (Join-Path $env:LOCALAPPDATA "hermes\scripts"),
        (Join-Path $env:USERPROFILE ".hermes\scripts")
    )
    foreach ($hermesScripts in $scriptDirs) {
        New-Item -ItemType Directory -Force -Path $hermesScripts -ErrorAction SilentlyContinue | Out-Null
        $targetScript = Join-Path $hermesScripts "sao_subconscious.py"
        if (Test-Path $saoScript) {
            Copy-Item -Path $saoScript -Destination $targetScript -Force -ErrorAction SilentlyContinue
            Write-Host "--> Subconscious script: $targetScript" -ForegroundColor DarkGray
        }
    }

    $listOut = Invoke-HermesCron -CronArgs @("cron", "list") 2>&1 | Out-String
    $hasDaily = $listOut -match "sao_subconscious|SAO Subconscious|Session Sync"
    if (-Not $hasDaily) {
        Write-Host "--> Registering SAO Subconscious cron (daily 09:00 + every 60m session sync)..." -ForegroundColor Yellow
        # schedule is POSITIONAL (not --schedule)
        # Hermes prints "Created job: ..." to stdout; exit code may be 0 even when stderr has warnings
        $out1 = Invoke-HermesCron -CronArgs @(
            "cron", "create", "0 9 * * *",
            "--name", "SAO Subconscious Daily",
            "--script", "sao_subconscious.py",
            "--no-agent",
            "--deliver", "local"
        ) 2>&1 | Out-String
        $out2 = Invoke-HermesCron -CronArgs @(
            "cron", "create", "every 60m",
            "--name", "SAO Session Sync 1h",
            "--script", "sao_subconscious.py",
            "--no-agent",
            "--deliver", "local"
        ) 2>&1 | Out-String
        $listAfter = Invoke-HermesCron -CronArgs @("cron", "list") 2>&1 | Out-String
        if ($listAfter -match "SAO Subconscious|SAO Session Sync|sao_subconscious") {
            Write-Host "    Cron registered OK (daily + hourly)." -ForegroundColor Green
            if ($listAfter -match "Gateway is not running|won't fire") {
                Write-Host "    Note: keep Hermes running so hourly sync fires." -ForegroundColor Yellow
            }
        } elseif (($out1 + $out2) -match "Created job") {
            Write-Host "    Cron created (verify: hermes cron list)." -ForegroundColor Green
        } else {
            Write-Host "    Cron create unclear. Check: hermes cron list" -ForegroundColor Yellow
            Write-Host $out1 -ForegroundColor DarkGray
            Write-Host $out2 -ForegroundColor DarkGray
        }
    } else {
        Write-Host "--> SAO subconscious cron already present." -ForegroundColor DarkGray
    }
} catch {
    Write-Host "   Auto-cron register skipped: $_" -ForegroundColor DarkGray
    Write-Host "   Manual:" -ForegroundColor DarkGray
    Write-Host '     hermes cron create "0 9 * * *" --name "SAO Subconscious Daily" --script sao_subconscious.py --no-agent --deliver local' -ForegroundColor DarkGray
}

# 5. Start Hermes (official entry: hermes)
#    Prefer Desktop (Electron) -> then Gateway -> then CLI Chat
Write-Host "--> Launching Hermes..." -ForegroundColor Yellow
Write-Host "    Graphify: managed by Hermes MCP (stdio), not a separate port." -ForegroundColor DarkGray

# We use the global/official Hermes executable (since install.ps1 doesn't clone to services/ anymore)
$globalExe = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\venv\Scripts\hermes.exe"
$globalBin = Join-Path $env:LOCALAPPDATA "hermes\bin\hermes.exe"
$dotLocal = Join-Path $env:USERPROFILE ".local\bin\hermes.exe"

function Resolve-HermesCommand {
    if (Test-Path $globalExe) { return @{ Kind="exe"; Path=$globalExe; WorkDir=$baseDir } }
    if (Test-Path $globalBin) { return @{ Kind="exe"; Path=$globalBin; WorkDir=$baseDir } }
    if (Test-Path $dotLocal) { return @{ Kind="exe"; Path=$dotLocal; WorkDir=$baseDir } }
    $onPath = Get-Command hermes -ErrorAction SilentlyContinue
    if ($onPath) { return @{ Kind="exe"; Path=$onPath.Source; WorkDir=$baseDir } }
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
    & $Cmd.Path -m hermes_cli.main @HermesArgs
    return $LASTEXITCODE
}

function Test-HermesMessagingConfigured {
    # True if Discord/Telegram/etc. looks configured (env or config)
    $envHints = @(
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN",
        "DISCORD_BOT_TOKEN", "DISCORD_TOKEN",
        "SLACK_BOT_TOKEN", "WHATSAPP_ENABLED"
    )
    foreach ($k in $envHints) {
        $v = [Environment]::GetEnvironmentVariable($k, "Process")
        if (-Not $v) { $v = [Environment]::GetEnvironmentVariable($k, "User") }
        if (-Not $v) { $v = [Environment]::GetEnvironmentVariable($k, "Machine") }
        if ($v) { return $true }
    }
    $paths = @(
        (Join-Path $env:LOCALAPPDATA "hermes\.env"),
        (Join-Path $env:USERPROFILE ".hermes\.env"),
        (Join-Path $env:LOCALAPPDATA "hermes\config.yaml"),
        (Join-Path $env:USERPROFILE ".hermes\config.yaml")
    )
    foreach ($p in $paths) {
        if (-Not (Test-Path $p)) { continue }
        try {
            $t = Get-Content $p -Raw -ErrorAction SilentlyContinue
            if ($t -match "(?i)(TELEGRAM_BOT_TOKEN|DISCORD_BOT_TOKEN|DISCORD_TOKEN)\s*=\s*\S+") { return $true }
            if ($t -match "(?i)(telegram|discord|slack|whatsapp):\s*\n(?:[^\n]*\n)*?\s+enabled:\s*true") { return $true }
        } catch { }
    }
    return $false
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

$hasMessaging = Test-HermesMessagingConfigured

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  What happens next" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Desktop Check
$desktopHasRun = $false
try {
    # Check if electron package installed or desktop app exists
    # Just try to launch desktop; if it works, we don't need chat.
    # We pass 'desktop' as a command so hermes_cli handles the electron spawn.
    # Since desktop returns immediately (spawns detached app), we just check exit code.
    Write-Host "  Trying Hermes Desktop..." -ForegroundColor DarkGray
    Push-Location $hermesCmd.WorkDir
    $deskExit = Invoke-Hermes -Cmd $hermesCmd -HermesArgs @("desktop")
    if ($deskExit -eq 0) {
        $desktopHasRun = $true
        Write-Host "  -> Hermes Desktop GUI opened." -ForegroundColor Green
        Write-Host "  -> Starting gateway in BACKGROUND so hourly cron can fire." -ForegroundColor Green
        Write-Host "  Tips: talk in Desktop. Sync memory via Desktop or CLI later." -ForegroundColor DarkGray
        Write-Host ""
    }
    Pop-Location
} catch { }

if ($desktopHasRun) {
    # Still background the gateway for cron if no messaging
    if (-Not $hasMessaging) {
        try {
            Start-Process -FilePath $hermesCmd.Path -ArgumentList @("gateway", "run") -WindowStyle Minimized
        } catch { }
    }
    exit 0
}

if ($hasMessaging) {
    Write-Host "  Messaging platform detected -> gateway (Discord/Telegram/etc.)" -ForegroundColor Green
    Write-Host "  Ctrl+C to stop gateway." -ForegroundColor DarkGray
    Write-Host ""
    Push-Location $hermesCmd.WorkDir
    try {
        Invoke-Hermes -Cmd $hermesCmd -HermesArgs @("gateway", "run")
    } finally {
        Pop-Location
    }
} else {
    Write-Host "  No Discord/Telegram configured yet." -ForegroundColor Yellow
    Write-Host "  -> Opening Hermes CHAT (type messages here)." -ForegroundColor Green
    Write-Host "  -> Starting gateway in BACKGROUND so hourly cron can fire." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Tips:" -ForegroundColor DarkGray
    Write-Host "    - Chat: type below, Enter to send" -ForegroundColor DarkGray
    Write-Host "    - After chat: open another CMD -> sao log list" -ForegroundColor DarkGray
    Write-Host "    - Later Discord/Telegram: hermes gateway setup" -ForegroundColor DarkGray
    Write-Host "    - Cron needs a running Hermes process (gateway bg or install service)" -ForegroundColor DarkGray
    Write-Host ""

    # Background gateway so cron scheduler lives even without messaging platforms
    try {
        if ($hermesCmd.Kind -eq "exe") {
            Start-Process -FilePath $hermesCmd.Path `
                -ArgumentList @("gateway", "run") `
                -WorkingDirectory $hermesCmd.WorkDir `
                -WindowStyle Minimized
        } else {
            Start-Process -FilePath $hermesCmd.Path `
                -ArgumentList @("-m", "hermes_cli.main", "gateway", "run") `
                -WorkingDirectory $hermesCmd.WorkDir `
                -WindowStyle Minimized
        }
        Write-Host "  Gateway started in minimized window (for cron)." -ForegroundColor DarkGray
    } catch {
        Write-Host "  Could not background gateway: $_" -ForegroundColor Yellow
        Write-Host "  Hourly sync may not fire until gateway runs." -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "  === HERMES CHAT (you can talk now) ===" -ForegroundColor Cyan
    Write-Host ""

    Push-Location $hermesCmd.WorkDir
    try {
        Invoke-Hermes -Cmd $hermesCmd -HermesArgs @("chat")
    } finally {
        Pop-Location
        Write-Host ""
        Write-Host "  Chat ended. Sync memory now:" -ForegroundColor Cyan
        Write-Host "    sao log" -ForegroundColor White
        Write-Host "    sao log list" -ForegroundColor White
        Write-Host "  Or wait for hourly cron (if gateway still running)." -ForegroundColor DarkGray
    }
}
