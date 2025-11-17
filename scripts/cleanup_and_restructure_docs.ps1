Param(
    [int]$Days = 15,
    [switch]$WhatIf
)

function Write-Section {
    Param(
        [string]$Path,
        [string]$Title
    )
    if (Test-Path $Path) {
        "# $Title"
        ""
        Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue
        ""
        "---"
        ""
    }
}

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $root "..")
Set-Location $repoRoot

$docsDir = Join-Path $repoRoot "docs"
if (-not (Test-Path $docsDir)) {
    throw "Docs folder not found: $docsDir"
}

$archiveDir = Join-Path $docsDir "archive"
New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null

# 1) Delete documents older than cutoff
$cutoff = (Get-Date).AddDays(-1 * [Math]::Abs($Days))
Write-Host "Removing files older than $Days days (modified before $cutoff) in '$docsDir'..." -ForegroundColor Yellow

$oldFiles = Get-ChildItem -LiteralPath $docsDir -File -Recurse -Force |
    Where-Object { $_.LastWriteTime -lt $cutoff }

foreach ($file in $oldFiles) {
    if ($WhatIf) {
        Write-Host "[WhatIf] Remove: $($file.FullName)"
    } else {
        Remove-Item -LiteralPath $file.FullName -Force -ErrorAction SilentlyContinue
        Write-Host "Removed: $($file.FullName)"
    }
}

# 2) Combine thematic sections
Write-Host "Combining thematic sections..." -ForegroundColor Yellow

# 2.1 DEPLOYMENT
# Base known ASCII-named files
$deploymentTargets = @(
    "docs\deployment\DEPLOYMENT_INSTRUCTIONS.md",
    "docs\deployment\PRODUCTION_READY_GUIDE.md",
    "docs\deployment\DEPLOY_VPS_LINUX_GUIDE.md",
    "docs\deployment\DOCKER_QUICK_DEPLOY.md",
    "docs\deployment\DOCKER_MIGRATION_PLAN.md",
    "docs\deployment\QUICK_DEPLOY_COMMANDS.md",
    "docs\SERVER_DEPLOYMENT.md",
    "docs\PRODUCTION_DATABASE_SETUP.md",
    "docs\PRODUCTION_DEPLOY.md",
    "docs\deployment\DEPLOYMENT_SUMMARY.md"
)
# Plus all other md files under docs/deployment (captures any non-ASCII names)
$deploymentDir = Join-Path $docsDir "deployment"
if (Test-Path $deploymentDir) {
    $extraDeploy = Get-ChildItem -LiteralPath $deploymentDir -File -Filter *.md -ErrorAction SilentlyContinue |
        ForEach-Object { $_.FullName.Substring($repoRoot.Path.Length + 1) }
    $deploymentTargets += $extraDeploy
    $deploymentTargets = $deploymentTargets | Select-Object -Unique
}
$deploymentOut = Join-Path $docsDir "DEPLOYMENT.md"
$deploymentContent = @()
foreach ($p in $deploymentTargets) {
    $full = Join-Path $repoRoot $p
    if (Test-Path $full) {
        $title = Split-Path $p -Leaf
        $deploymentContent += (Write-Section -Path $full -Title $title)
    }
}
if ($deploymentContent.Count -gt 0) {
    if ($WhatIf) {
        Write-Host "[WhatIf] Generate: $deploymentOut"
    } else {
        $deploymentContent | Set-Content -LiteralPath $deploymentOut -Encoding UTF8
        Write-Host "Generated: $deploymentOut"
    }
    # Move sources to archive
    foreach ($p in $deploymentTargets) {
        $src = Join-Path $repoRoot $p
        if (Test-Path $src) {
            $dst = Join-Path $archiveDir (Split-Path $p -Leaf)
            if ($WhatIf) {
                Write-Host "[WhatIf] Move: $src -> $dst"
            } else {
                Move-Item -LiteralPath $src -Destination $dst -Force
                Write-Host "Moved: $src -> $dst"
            }
        }
    }
}

# 2.2 QUICKSTART / INSTALLATION
$quickTargets = @(
    "docs\QUICKSTART.md",
    "docs\INSTALLATION.md",
    "docs\user-guides\START_AFTER_FIXES.md",
    "docs\user-guides\START_HERE.txt"
)
# Include any other files in user-guides as part of quickstart collection
$userGuidesDir = Join-Path $docsDir "user-guides"
if (Test-Path $userGuidesDir) {
    $extraGuides = Get-ChildItem -LiteralPath $userGuidesDir -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in ".md", ".txt" } |
        ForEach-Object { $_.FullName.Substring($repoRoot.Path.Length + 1) }
    $quickTargets += $extraGuides
    $quickTargets = $quickTargets | Select-Object -Unique
}
$quickOut = Join-Path $docsDir "QUICKSTART_COMBINED.md"
$quickContent = @()
foreach ($p in $quickTargets) {
    $full = Join-Path $repoRoot $p
    if (Test-Path $full) {
        $title = Split-Path $p -Leaf
        $quickContent += (Write-Section -Path $full -Title $title)
    }
}
if ($quickContent.Count -gt 0) {
    if ($WhatIf) {
        Write-Host "[WhatIf] Generate: $quickOut"
    } else {
        $quickContent | Set-Content -LiteralPath $quickOut -Encoding UTF8
        Write-Host "Generated: $quickOut"
    }
    foreach ($p in $quickTargets) {
        $src = Join-Path $repoRoot $p
        if (Test-Path $src) {
            $dst = Join-Path $archiveDir (Split-Path $p -Leaf)
            if ($WhatIf) {
                Write-Host "[WhatIf] Move: $src -> $dst"
            } else {
                Move-Item -LiteralPath $src -Destination $dst -Force
                Write-Host "Moved: $src -> $dst"
            }
        }
    }
}

# 2.3 TROUBLESHOOTING
$troubleDir = Join-Path $docsDir "troubleshooting"
$troubleOut = Join-Path $docsDir "TROUBLESHOOTING.md"
if (Test-Path $troubleDir) {
    $troubleFiles = Get-ChildItem -LiteralPath $troubleDir -File -Filter *.md -ErrorAction SilentlyContinue
    $troubleContent = @()
    foreach ($f in $troubleFiles) {
        $rel = $f.FullName.Substring($repoRoot.Path.Length + 1)
        $troubleContent += (Write-Section -Path $f.FullName -Title (Split-Path $rel -Leaf))
    }
    if ($troubleContent.Count -gt 0) {
        if ($WhatIf) {
            Write-Host "[WhatIf] Generate: $troubleOut"
        } else {
            $troubleContent | Set-Content -LiteralPath $troubleOut -Encoding UTF8
            Write-Host "Generated: $troubleOut"
        }
        foreach ($f in $troubleFiles) {
            $dst = Join-Path $archiveDir $f.Name
            if ($WhatIf) {
                Write-Host "[WhatIf] Move: $($f.FullName) -> $dst"
            } else {
                Move-Item -LiteralPath $f.FullName -Destination $dst -Force
                Write-Host "Moved: $($f.FullName) -> $dst"
            }
        }
    }
}

# 2.4 Migrations
$migrationsTargets = @(
    "docs\MIGRATIONS_GUIDE.md",
    "docs\migration\MIGRATION_GUIDE.md",
    "docs\SQLALCHEMY_ORM_UPDATE.md",
    "docs\ORM_MIGRATION_PLAN.md",
    "docs\ORM_MIGRATION_COMPLETE.md",
    "docs\SQLITE_MIGRATIONS_FIX.md"
)
$migrationsOut = Join-Path $docsDir "MIGRATIONS.md"
$migrationsContent = @()
foreach ($p in $migrationsTargets) {
    $full = Join-Path $repoRoot $p
    if (Test-Path $full) {
        $title = Split-Path $p -Leaf
        $migrationsContent += (Write-Section -Path $full -Title $title)
    }
}
if ($migrationsContent.Count -gt 0) {
    if ($WhatIf) {
        Write-Host "[WhatIf] Generate: $migrationsOut"
    } else {
        $migrationsContent | Set-Content -LiteralPath $migrationsOut -Encoding UTF8
        Write-Host "Generated: $migrationsOut"
    }
    foreach ($p in $migrationsTargets) {
        $src = Join-Path $repoRoot $p
        if (Test-Path $src) {
            $dst = Join-Path $archiveDir (Split-Path $p -Leaf)
            if ($WhatIf) {
                Write-Host "[WhatIf] Move: $src -> $dst"
            } else {
                Move-Item -LiteralPath $src -Destination $dst -Force
                Write-Host "Moved: $src -> $dst"
            }
        }
    }
}

# 3) Update docs/README.md
$readmePath = Join-Path $docsDir "README.md"
$readmeContent = @()
$readmeContent += "# Documentation"
$readmeContent += ""
$readmeContent += "## Index"
$readmeContent += ""
if (Test-Path $deploymentOut) { $readmeContent += "* [DEPLOYMENT](./DEPLOYMENT.md)" }
if (Test-Path $quickOut) { $readmeContent += "* [QUICKSTART](./QUICKSTART_COMBINED.md)" }
if (Test-Path $troubleOut) { $readmeContent += "* [TROUBLESHOOTING](./TROUBLESHOOTING.md)" }
if (Test-Path $migrationsOut) { $readmeContent += "* [MIGRATIONS](./MIGRATIONS.md)" }
if (Test-Path (Join-Path $docsDir "CHANGELOG.md")) { $readmeContent += "* [CHANGELOG](./CHANGELOG.md)" }
if (Test-Path (Join-Path $docsDir "WORKFLOW.md")) { $readmeContent += "* [WORKFLOW](./WORKFLOW.md)" }
if (Test-Path (Join-Path $docsDir "CONTRIBUTING.md")) { $readmeContent += "* [CONTRIBUTING](./CONTRIBUTING.md)" }
$readmeContent += "* [ARCHIVE](./archive/) - outdated and duplicate files moved here"
$readmeContent += ""
$readmeContent += "Cleanup script: `scripts/cleanup_and_restructure_docs.ps1` (params: `-Days`, `-WhatIf`)."

if ($WhatIf) {
    Write-Host "[WhatIf] Update: $readmePath"
} else {
    $readmeContent | Set-Content -LiteralPath $readmePath -Encoding UTF8
    Write-Host "Updated: $readmePath"
}

Write-Host "Done." -ForegroundColor Green


