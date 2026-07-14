# scripts/install.ps1
# SAO install: official Hermes (install.ps1 Nous) + Graphify + SAO skills
# ASCII-only comments for PowerShell 5.1 compatibility.
# Does NOT git-clone hermes-agent into services/hermes (official path preferred).

param(
    # Build/include Hermes Desktop when official installer supports it
    [switch]$Desktop = $true,
    # Skip Hermes install if hermes already on PATH / LOCALAPPDATA
    [switch]$SkipHermesIfPresent = $true
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Installing SAO (Sira Agentic Orchestrator)" -ForegroundColor Cyan
Write-Host "  Hermes: official installer (not git clone)" -ForegroundColor Cyan
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
    $uvLocal = Join-Path $env:USERPROFILE ".local\bin"
    $uvCargo = Join-Path $env:USERPROFILE ".cargo\bin"
    $hermesBin = Join-Path $env:LOCALAPPDATA "hermes\bin"
    $hermesVenv = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\venv\Scripts"
    if (Test-Path $uvLocal) { $env:Path = "$uvLocal;$env:Path" }
    if (Test-Path $uvCargo) { $env:Path = "$uvCargo;$env:Path" }
    if (Test-Path $hermesBin) { $env:Path = "$hermesBin;$env:Path" }
    if (Test-Path $hermesVenv) { $env:Path = "$hermesVenv;$env:Path" }
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

function Test-HermesInstalled {
    Refresh-Path
    if (Test-Command "hermes") { return $true }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\venv\Scripts\hermes.exe"),
        (Join-Path $env:LOCALAPPDATA "hermes\bin\hermes.exe"),
        (Join-Path $env:USERPROFILE ".local\bin\hermes.exe")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $true }
    }
    return $false
}

function Install-OfficialHermes {
    Write-Host "--> Installing Hermes via official Nous installer..." -ForegroundColor Yellow
    Write-Host "    URL: https://hermes-agent.nousresearch.com/install.ps1" -ForegroundColor DarkGray
    if ($Desktop) {
        Write-Host "    Mode: CLI + Desktop (IncludeDesktop when supported)" -ForegroundColor DarkGray
    } else {
        Write-Host "    Mode: CLI only" -ForegroundColor DarkGray
    }

    # Download then invoke so we can pass switches (-IncludeDesktop).
    # irm|iex alone cannot pass -IncludeDesktop reliably.
    $tmp = Join-Path $env:TEMP ("sao-hermes-install-" + [guid]::NewGuid().ToString("N") + ".ps1")
    try {
        Invoke-WebRequest -Uri "https://hermes-agent.nousresearch.com/install.ps1" -OutFile $tmp -UseBasicParsing
        $args = @("-ExecutionPolicy", "Bypass", "-File", $tmp, "-SkipSetup")
        if ($Desktop) {
            # Official installer flag (opt-in desktop build). Safe if ignored on older scripts.
            $args += "-IncludeDesktop"
        }
        Write-Host "    Running official install.ps1 (may take several minutes)..." -ForegroundColor Cyan
        $psHost = (Get-Process -Id $PID).Path
        if (-Not $psHost) { $psHost = "powershell" }
        & $psHost @args
        $code = $LASTEXITCODE
        if ($code -ne 0 -and $null -ne $code) {
            Write-Host "    Official installer exit code: $code" -ForegroundColor Yellow
            # Retry without IncludeDesktop if desktop flag broke older installer
            if ($Desktop) {
                Write-Host "    Retry without -IncludeDesktop..." -ForegroundColor Yellow
                & $psHost -ExecutionPolicy Bypass -File $tmp -SkipSetup
            }
        }
    } finally {
        Remove-Item -Force $tmp -ErrorAction SilentlyContinue
    }

    Refresh-Path

    if (-Not (Test-HermesInstalled)) {
        Write-Host "    WARNING: hermes still not found after official install." -ForegroundColor Yellow
        Write-Host "    Manual: iex (irm https://hermes-agent.nousresearch.com/install.ps1)" -ForegroundColor Yellow
        Write-Host "    Or Desktop installer: https://hermes-agent.nousresearch.com/" -ForegroundColor Yellow
        return $false
    }

    Write-Host "--> Hermes official install OK" -ForegroundColor Green
    if (Test-Command "hermes") {
        try {
            $v = & hermes --version 2>$null
            if ($v) { Write-Host "    hermes: $v" -ForegroundColor DarkGray }
        } catch { }
    }
    return $true
}

function Install-Graphify {
    # Graphify is SAO-managed (not part of Hermes). Prefer services/ clone + uv, else pip.
    $target = Join-Path $baseDir "services\graphify"
    $url = "https://github.com/Graphify-Labs/graphify.git"

    Write-Host "--> Installing Graphify (knowledge graph for vault)..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path (Join-Path $baseDir "services") | Out-Null

    if (-Not (Test-Path $target)) {
        if (-Not (Test-Command "git")) {
            Write-Host "    Git missing; trying: uv pip install graphify (or pip)" -ForegroundColor Yellow
        } else {
            Write-Host "    Cloning graphify (shallow)..." -ForegroundColor DarkGray
            git clone --depth 1 $url $target
            Remove-Item -Recurse -Force "$target\.git" -ErrorAction SilentlyContinue
        }
    } else {
        Write-Host "    services\graphify already present." -ForegroundColor DarkGray
    }

    if (Test-Path $target) {
        Push-Location $target
        try {
            uv venv
            uv pip install -e .
            Write-Host "--> Graphify venv ready: $target" -ForegroundColor Green
        } catch {
            Write-Host "    Graphify local install failed: $_" -ForegroundColor Yellow
            Write-Host "    Fallback: uv pip install graphify (or pip install graphify)" -ForegroundColor Yellow
        } finally {
            Pop-Location
        }
    } else {
        try {
            uv pip install graphify
            Write-Host "--> Graphify installed via uv pip" -ForegroundColor Green
        } catch {
            Write-Host "    Could not install graphify automatically." -ForegroundColor Yellow
            Write-Host "    Manual: pip install graphify  OR  git clone Graphify-Labs/graphify" -ForegroundColor Yellow
        }
    }
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

Write-Host "`n[0/4] Checking prerequisites..." -ForegroundColor Yellow

if (-Not (Test-Command "npm")) {
    throw "Node.js/npm not found. Install Node.js 20+: https://nodejs.org"
}
# Git optional if Hermes already installed and Graphify comes from pip
if (-Not (Test-Command "git")) {
    Write-Host "    Git not on PATH (needed only if Graphify clone required)." -ForegroundColor Yellow
}

Ensure-Uv

Write-Host "`n[1/4] Hermes (official Nous installer)..." -ForegroundColor Yellow
$needHermes = $true
if ($SkipHermesIfPresent -and (Test-HermesInstalled)) {
    Write-Host "--> Hermes already present. Skip reinstall (use -SkipHermesIfPresent:`$false to force)." -ForegroundColor Green
    $needHermes = $false
}
if ($needHermes) {
    $ok = Install-OfficialHermes
    if (-Not $ok) {
        Write-Host "    SAO will continue; fix Hermes then re-run: sao install" -ForegroundColor Yellow
    }
} else {
    Refresh-Path
}

Write-Host "`n[2/4] Graphify..." -ForegroundColor Yellow
Install-Graphify

Write-Host "`n[3/4] SAO skills -> Hermes skills dir..." -ForegroundColor Yellow
$skillsDir = Join-Path $env:LOCALAPPDATA "hermes\skills"
New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null
if (Test-Path "skills") {
    Get-ChildItem -Path "skills" -Filter "*.md" | ForEach-Object {
        $dest = Join-Path $skillsDir $_.Name
        Copy-Item -Path $_.FullName -Destination $dest -Force
        Write-Host "   --> Skill installed: $($_.Name)" -ForegroundColor Green
    }
} else {
    Write-Host "   No skills/ folder in package." -ForegroundColor Yellow
}

# Subconscious script for cron (relative script path under Hermes home)
$scriptsDir = Join-Path $env:LOCALAPPDATA "hermes\scripts"
New-Item -ItemType Directory -Force -Path $scriptsDir | Out-Null
$subSrc = Join-Path $baseDir "scripts\subconscious.py"
if (Test-Path $subSrc) {
    Copy-Item -Path $subSrc -Destination (Join-Path $scriptsDir "sao_subconscious.py") -Force
    Write-Host "   --> sao_subconscious.py -> $scriptsDir" -ForegroundColor Green
}
# Also ~/.hermes/scripts for non-Windows layout
$dotScripts = Join-Path $env:USERPROFILE ".hermes\scripts"
try {
    New-Item -ItemType Directory -Force -Path $dotScripts | Out-Null
    if (Test-Path $subSrc) {
        Copy-Item -Path $subSrc -Destination (Join-Path $dotScripts "sao_subconscious.py") -Force
    }
} catch { }

Write-Host "`n[4/4] SAO local state + worker probe..." -ForegroundColor Yellow
$workers = @("claude", "opencode", "codex", "aider", "cursor")
$found = @()
foreach ($w in $workers) {
    if (Test-Command $w) {
        $found += $w
        Write-Host "   found: $w" -ForegroundColor Green
    }
}
if ($found.Count -eq 0) {
    Write-Host "   No external worker CLI. Default worker = sira (Hermes)." -ForegroundColor Yellow
} else {
    Write-Host "   Tip: sao set worker $($found[0])" -ForegroundColor Cyan
}

Write-Host "--> CLI package: sira-agentic-orchestrator (npm global)." -ForegroundColor DarkGray

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "  Hermes: official (CLI; Desktop if -IncludeDesktop OK)" -ForegroundColor Green
Write-Host "  Graphify: SAO-managed (vault knowledge graph)" -ForegroundColor Green
Write-Host "  NOT used: git clone hermes into services/hermes" -ForegroundColor Green
Write-Host "  Next steps:" -ForegroundColor Green
Write-Host "    1. hermes setup          (model/provider wizard)" -ForegroundColor Green
Write-Host "    2. sao create vault" -ForegroundColor Green
Write-Host "    3. sao start             (prefers Desktop if available)" -ForegroundColor Green
Write-Host "    Optional: hermes desktop / hermes gui" -ForegroundColor Green
Write-Host "    Optional: hermes gateway install  (cron always-on)" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
