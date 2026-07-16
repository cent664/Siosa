# PoE Wiki Agent — one-click launcher (API + React UI on :8000)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$venvActivate = Join-Path $Root ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    Write-Error "Virtual environment not found. Run: python -m venv .venv; pip install -e `".[dev,speech]`""
    exit 1
}

. $venvActivate

function Resolve-NpmOnPath {
    if (Get-Command npm -ErrorAction SilentlyContinue) { return $true }

    $candidates = @(
        (Join-Path $env:ProgramFiles "nodejs"),
        (Join-Path ${env:ProgramFiles(x86)} "nodejs"),
        (Join-Path $env:LOCALAPPDATA "nodejs")
    )

    foreach ($nodeDir in $candidates) {
        if (Test-Path (Join-Path $nodeDir "npm.cmd")) {
            $env:Path = "$nodeDir;$env:Path"
            return $true
        }
    }

    return $false
}

if (-not (Resolve-NpmOnPath)) {
    Write-Error @"
npm not found. Node.js is required to build the web UI.

Install Node.js LTS, then close and reopen this window:
  winget install OpenJS.NodeJS.LTS
  https://nodejs.org/

Or manually: cd web; npm install; npm run build
"@
    exit 1
}

Write-Host "Building web UI..."
Push-Location (Join-Path $Root "web")
npm install
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
npm run build
Pop-Location
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "  App:      http://127.0.0.1:8000/"
Write-Host "  API:      http://127.0.0.1:8000"
Write-Host "  Docs:     http://127.0.0.1:8000/docs/"
Write-Host ""
Write-Host "Press Ctrl+C to stop."
Write-Host ""

uvicorn poe_agent.harness.api.app:app --host 127.0.0.1 --port 8000
