# Builds transfer/ for copying to another machine (USB, OneDrive, etc.).
# transfer/ is gitignored — never push to GitHub.
# Usage: .\scripts\export_transfer.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$TransferRoot = Join-Path $ProjectRoot "transfer"
$CursorHome = Join-Path $env:USERPROFILE ".cursor"
$TranscriptsRoot = Join-Path $CursorHome "projects\c-Users-adg00-Desktop-Project\agent-transcripts"
$PlansRoot = Join-Path $CursorHome "plans"
$SkillsRoot = Join-Path $CursorHome "skills-cursor"

function Ensure-Dir($path) {
    if (-not (Test-Path $path)) { New-Item -ItemType Directory -Path $path -Force | Out-Null }
}

function Copy-Tree($src, $dst) {
    if (-not (Test-Path $src)) { return 0 }
    Ensure-Dir $dst
    $count = 0
    Get-ChildItem -Path $src -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($src.Length).TrimStart("\")
        $target = Join-Path $dst $rel
        Ensure-Dir (Split-Path $target -Parent)
        Copy-Item $_.FullName $target -Force
        $count++
    }
    return $count
}

Write-Host "Exporting laptop transfer bundle to $TransferRoot ..."

if (Test-Path $TransferRoot) {
    Remove-Item -Path $TransferRoot -Recurse -Force
}

$dirs = @(
    "$TransferRoot\cursor\project-rules",
    "$TransferRoot\cursor\plans",
    "$TransferRoot\cursor\agent-transcripts",
    "$TransferRoot\skills",
    "$TransferRoot\env",
    "$TransferRoot\railway"
)
foreach ($d in $dirs) { Ensure-Dir $d }

# Git metadata
$gitCommit = "unknown"
$gitBranch = "unknown"
Push-Location $ProjectRoot
try {
    $gitCommit = (git rev-parse --short HEAD 2>$null)
    $gitBranch = (git branch --show-current 2>$null)
} finally { Pop-Location }

# Project Cursor rules
$rulesSrc = Join-Path $ProjectRoot ".cursor\rules"
$rulesCount = Copy-Tree $rulesSrc "$TransferRoot\cursor\project-rules"

# Agent transcripts (full jsonl)
$transcriptCount = Copy-Tree $TranscriptsRoot "$TransferRoot\cursor\agent-transcripts"

# Plans: Siosa / PoE wiki agent related filenames
$planKeywords = @(
    "siosa", "poe", "wiki", "railway", "deploy", "prod", "retrieval", "architecture",
    "streamlit", "react", "hosting", "cloud", "trace", "changelog", "laptop", "sync"
)
$planCount = 0
if (Test-Path $PlansRoot) {
    Get-ChildItem -Path $PlansRoot -Filter "*.plan.md" -File | ForEach-Object {
        $name = $_.Name.ToLower()
        $match = $false
        foreach ($kw in $planKeywords) {
            if ($name -like "*$kw*") { $match = $true; break }
        }
        if ($match) {
            Copy-Item $_.FullName (Join-Path "$TransferRoot\cursor\plans" $_.Name) -Force
            $planCount++
        }
    }
}

# Skills index
$skillsIndex = Join-Path "$TransferRoot\skills" "SKILLS_INDEX.md"
$skillLines = @(
    "# Cursor skills on this machine",
    "",
    "Path: $SkillsRoot",
    "",
    "| Skill folder | SKILL.md |",
    "|--------------|----------|"
)
if (Test-Path $SkillsRoot) {
    Get-ChildItem -Path $SkillsRoot -Directory | Sort-Object Name | ForEach-Object {
        $skillMd = Join-Path $_.FullName "SKILL.md"
        $has = if (Test-Path $skillMd) { "yes" } else { "no" }
        $skillLines += "| $($_.Name) | $has |"
    }
} else {
    $skillLines += "| (skills folder not found) | |"
}
$skillLines | Set-Content -Path $skillsIndex -Encoding UTF8

# Env templates and local backup
Copy-Item (Join-Path $ProjectRoot ".env.example") "$TransferRoot\env\.env.example" -Force -ErrorAction SilentlyContinue
$envLocal = Join-Path $ProjectRoot ".env"
if (Test-Path $envLocal) {
    $banner = @(
        "# WARNING: CONTAINS SECRETS. Do not commit, email, or upload to public cloud.",
        "# Copy to project root as .env on your laptop only.",
        ""
    )
    $content = Get-Content $envLocal -Raw
    ($banner -join "`n") + $content | Set-Content "$TransferRoot\env\.env.local.backup" -Encoding UTF8
    Write-Host "  Copied .env -> transfer/env/.env.local.backup (contains secrets)"
} else {
    "# No .env on this machine. Create from transfer/env/.env.example on the laptop." |
        Set-Content "$TransferRoot\env\.env.local.backup" -Encoding UTF8
}

# Railway reference
Copy-Item (Join-Path $ProjectRoot "railway.variables.example") "$TransferRoot\railway\railway.variables.example" -Force

# Project overview (committed source -> transfer bundle)
$overviewSrc = Join-Path $ProjectRoot "docs\PROJECT_OVERVIEW.txt"
if (Test-Path $overviewSrc) {
    Copy-Item $overviewSrc "$TransferRoot\PROJECT_OVERVIEW.txt" -Force
    Write-Host "  Copied docs/PROJECT_OVERVIEW.txt"
}
@(
    "# Production Railway Variables (no real keys in this file)",
    "",
    "See railway.variables.example in this folder.",
    "",
    "Required on Railway for https://www.poesiosa.net/:",
    "- DEPLOYMENT_PROFILE=production",
    "- POE_PROVIDER_MODE=claude",
    "- ANTHROPIC_API_KEY=your key",
    "- INLINE_EVAL=false",
    "- POE_ENABLE_OLLAMA=false",
    "- RETRIEVAL_MODE=live",
    "- POE_DATA_DIR=/app/data",
    "",
    "Remove: JUDGE_PROVIDER=ollama, OLLAMA_*, POE_API_HOST, POE_API_PORT, custom PORT"
) | Set-Content "$TransferRoot\railway\production-variables.md" -Encoding UTF8

# User rules placeholder (global rules are not stored in the repo)
$userRulesPath = "$TransferRoot\cursor\user-rules.md"
@(
    "# Cursor user rules (global)",
    "",
    "Global user rules live in **Cursor Settings -> Rules -> User rules**, not in the repo.",
    "",
    "On this PC: open Cursor Settings, copy all User rules text, and paste below.",
    "On the laptop: paste the same text into Cursor Settings -> Rules -> User rules.",
    "",
    "---",
    "",
    "(Paste your user rules below this line)",
    ""
) | Set-Content -Path $userRulesPath -Encoding UTF8

# HANDOFF.md
$changelogPath = Join-Path $ProjectRoot "docs\CHANGELOG.md"
$changelogSnippet = ""
if (Test-Path $changelogPath) {
    $changelogSnippet = (Get-Content $changelogPath -TotalCount 35) -join "`n"
}

$handoff = @"
# PoE Wiki Agent - laptop handoff

Exported: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Machine: $env:COMPUTERNAME
Git: $gitBranch @ $gitCommit
Repo: https://github.com/cent664/Siosa

## Production

- Public URL: https://www.poesiosa.net/
- Hosting: Railway, deploy on push to main
- Booth mode: DEPLOYMENT_PROFILE=production or INLINE_EVAL=false + POE_ENABLE_OLLAMA=false
- API keys only in Railway Variables and local .env (never git)

## What this transfer folder contains

| Path | Purpose |
|------|---------|
| env/.env.local.backup | Your local secrets (if .env existed) |
| cursor/agent-transcripts/ | Past Cursor agent chats for this project |
| cursor/plans/ | Saved plan files ($planCount copied) |
| cursor/project-rules/ | Copy of .cursor/rules/ ($rulesCount files) |
| cursor/user-rules.md | Paste global Cursor user rules here |
| railway/ | Production variable templates |
| skills/SKILLS_INDEX.md | Installed Cursor skills on this PC |
| PROJECT_OVERVIEW.txt | Full technical choices and transfer instructions |

## Laptop quick start

1. git clone https://github.com/cent664/Siosa.git
2. Copy this entire transfer/ folder into the cloned repo root.
3. Read PROJECT_OVERVIEW.txt (technical overview + transfer steps)
4. copy transfer\env\.env.local.backup .env (or use .env.example and add keys)
5. Follow docs/LAPTOP_SETUP.md in the repo.
6. New Cursor chat: Read transfer/PROJECT_OVERVIEW.txt and docs/ARCHITECTURE.md

## Recent changelog (excerpt)

$changelogSnippet
"@
$handoff | Set-Content "$TransferRoot\HANDOFF.md" -Encoding UTF8

# README + manifest
@(
    "# transfer/ - local handoff bundle",
    "",
    "This folder is **gitignored**. Copy it to your laptop with USB / OneDrive / network share.",
    "",
    "Regenerate on this PC: .\scripts\export_transfer.ps1",
    "",
    "Do **not** commit or upload to public GitHub (may contain API keys in env backup and chats).",
    "",
    "Start on laptop: read PROJECT_OVERVIEW.txt then HANDOFF.md."
) | Set-Content "$TransferRoot\README.md" -Encoding UTF8

$manifest = @{
    exported_at = (Get-Date).ToUniversalTime().ToString("o")
    hostname    = $env:COMPUTERNAME
    git_commit  = $gitCommit
    git_branch  = $gitBranch
    counts      = @{
        project_rules     = $rulesCount
        agent_transcripts = $transcriptCount
        plans             = $planCount
    }
    paths       = @{
        transcripts_source = $TranscriptsRoot
        plans_source       = $PlansRoot
    }
} | ConvertTo-Json -Depth 4
$manifest | Set-Content "$TransferRoot\manifest.json" -Encoding UTF8

Write-Host "Done."
Write-Host "  Rules: $rulesCount | Transcripts: $transcriptCount | Plans: $planCount"
Write-Host "  Output: $TransferRoot"
Write-Host "Copy transfer/ to your laptop (not via git push)."
