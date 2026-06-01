# PoE Wiki Agent — one-click launcher (API + React UI on :8000)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location $Root



$venvActivate = Join-Path $Root ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $venvActivate)) {

    Write-Error "Virtual environment not found. Run: python -m venv .venv; pip install -e `".[dev,speech]`""

    exit 1

}



. $venvActivate



$distIndex = Join-Path $Root "web\dist\index.html"

if (-not (Test-Path $distIndex)) {

    Write-Host "Building web UI..."

    $npm = Get-Command npm -ErrorAction SilentlyContinue

    if (-not $npm) {

        Write-Error "npm not found. Install Node.js, then: cd web; npm install; npm run build"

        exit 1

    }

    Push-Location (Join-Path $Root "web")

    npm install

    if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }

    npm run build

    Pop-Location

    if ($LASTEXITCODE -ne 0) { exit 1 }

}



Write-Host ""

Write-Host "  App:      http://127.0.0.1:8000/"

Write-Host "  API:      http://127.0.0.1:8000"

Write-Host "  Docs:     http://127.0.0.1:8000/docs/"

Write-Host ""

Write-Host "Press Ctrl+C to stop."

Write-Host ""



uvicorn poe_agent.harness.api.app:app --host 127.0.0.1 --port 8000

