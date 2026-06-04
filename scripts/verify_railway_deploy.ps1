# Usage:
#   .\scripts\verify_railway_deploy.ps1 -BaseUrl "https://siosa-production.up.railway.app"
#   .\scripts\verify_railway_deploy.ps1 -BaseUrl "https://www.poesiosa.net"
# See DEPLOY.md "Custom domain" for DNS setup. Exit 0 = healthy; 2 = missing API keys.
param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl
)

$BaseUrl = $BaseUrl.TrimEnd("/")
$exitCode = 0

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

if ($health.inline_eval -eq $true) {
    Write-Host "WARN inline_eval is true - judges run on every Ask. Set INLINE_EVAL=false or DEPLOYMENT_PROFILE=production."
    $exitCode = 2
}
if ($health.dev_ui_enabled -eq $false) {
    Write-Host "WARN dev_ui_enabled is false - timing/trace/score hidden. Set DEV_UI_ENABLED=true in Railway Variables."
    $exitCode = 2
}
if ($health.deployment_hint) {
    Write-Host "WARN deployment_hint: $($health.deployment_hint)"
    $exitCode = 2
}
if ($health.judge_provider -notin @("claude", "gpt4")) {
    Write-Host "WARN judge_provider is $($health.judge_provider) - set JUDGE_PROVIDER=claude or DEPLOYMENT_PROFILE=production"
    $exitCode = 2
}
if ($health.provider_mode -eq "stub") {
    Write-Host "WARN provider_mode is stub - set POE_PROVIDER_MODE=claude and ANTHROPIC_API_KEY in Railway"
    $exitCode = 2
}

$provider = Test-Endpoint "/settings/provider" $true
if (-not $provider) { exit 1 }
$claudeOk = ($provider.available_modes | Where-Object { $_.id -eq "claude" }).available
$gpt4Ok = ($provider.available_modes | Where-Object { $_.id -eq "gpt4" }).available
if (-not $claudeOk -and -not $gpt4Ok) {
    Write-Host "WARN Claude and GPT-4 unavailable - add ANTHROPIC_API_KEY and OPENAI_API_KEY in Railway Variables, then redeploy."
    Write-Host "      See railway.variables.example in the repo."
    $exitCode = 2
}
if ($provider.mode -eq "stub") {
    Write-Host "WARN Active provider is stub - set POE_PROVIDER_MODE=claude (or pick Claude in the UI after keys are set)."
    $exitCode = 2
}

$root = Test-Endpoint "/" $false
if (-not $root) { exit 1 }

if ($exitCode -eq 0) {
    Write-Host "Public deploy OK. Booth mode active. Cloud providers enabled. Run one Ask."
} else {
    Write-Host "Deploy reachable but production Variables need attention. See DEPLOY.md and railway.variables.example."
}
exit $exitCode
