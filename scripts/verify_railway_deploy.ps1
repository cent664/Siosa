# Usage: .\scripts\verify_railway_deploy.ps1 -BaseUrl "https://YOUR-DOMAIN.up.railway.app"
param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl
)

$BaseUrl = $BaseUrl.TrimEnd("/")

function Test-Endpoint($Path, $ExpectJson) {
    $url = "$BaseUrl$Path"
    try {
        $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 60
    } catch {
        Write-Host "FAIL $Path : $($_.Exception.Message)"
        return $false
    }
    Write-Host "OK   $Path -> $($resp.StatusCode)"
    if ($ExpectJson) {
        $body = $resp.Content | ConvertFrom-Json
        Write-Host "     $Path body: $($resp.Content)"
        return $body
    }
    return $true
}

Write-Host "Checking $BaseUrl ..."
$live = Test-Endpoint "/health/live" $true
if (-not $live -or $live.status -ne "ok") { exit 1 }

$health = Test-Endpoint "/health" $true
if (-not $health -or $health.status -ne "ok") { exit 1 }
if ($health.judge_provider -eq "ollama") {
    Write-Host "WARN judge_provider is ollama — set JUDGE_PROVIDER=claude in Railway Variables"
}
if ($health.provider_mode -eq "stub") {
    Write-Host "WARN provider_mode is stub — set POE_PROVIDER_MODE=claude and API keys in Railway"
}

$root = Test-Endpoint "/" $false
if (-not $root) { exit 1 }

Write-Host "All checks passed. Run one Ask in the browser to confirm cloud answers."
