Param(
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $root "..")
Set-Location $repoRoot

function Ensure-Dir {
    Param([string]$Path)
    if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Force -Path $Path | Out-Null }
}

function Move-Safe {
    Param(
        [string]$Src,
        [string]$DstDir
    )
    if (-not (Test-Path $Src)) { return }
    Ensure-Dir -Path $DstDir
    $dst = Join-Path $DstDir (Split-Path $Src -Leaf)
    if ($WhatIf) {
        Write-Host "[WhatIf] Move: $Src -> $dst"
    } else {
        Move-Item -LiteralPath $Src -Destination $dst -Force
        Write-Host "Moved: $Src -> $dst"
    }
}

# 1) Скрипты
$scriptsWin = Join-Path $repoRoot "scripts\windows"
$scriptsUnix = Join-Path $repoRoot "scripts\unix"

Get-ChildItem -LiteralPath $repoRoot -File -Filter *.bat | ForEach-Object {
    Move-Safe -Src $_.FullName -DstDir $scriptsWin
}
Get-ChildItem -LiteralPath $repoRoot -File -Filter *.cmd | ForEach-Object {
    Move-Safe -Src $_.FullName -DstDir $scriptsWin
}
Get-ChildItem -LiteralPath $repoRoot -File -Filter *.sh | ForEach-Object {
    Move-Safe -Src $_.FullName -DstDir $scriptsUnix
}

# 2) Отчёты/покрытие (минимально и безопасно)
$coverageDir = Join-Path $repoRoot "reports\coverage"
Move-Safe -Src (Join-Path $repoRoot "coverage.xml") -DstDir $coverageDir

# 3) Только явные временные логи в корне
$tmpDir = Join-Path $repoRoot "tmp"
Get-ChildItem -LiteralPath $repoRoot -File -Filter *.log -ErrorAction SilentlyContinue | ForEach-Object {
    Move-Safe -Src $_.FullName -DstDir $tmpDir
}

Write-Host "Root organization completed." -ForegroundColor Green


