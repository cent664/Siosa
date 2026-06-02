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
    Write-Host "WARN judge_provider is ollama - set JUDGE_PROVIDER=claude in Railway Variables"
}
if ($health.provider_mode -eq "stub") {
    Write-Host "WARN provider_mode is stub - set POE_PROVIDER_MODE=claude and API keys in Railway"
}

$provider = Test-Endpoint "/settings/provider" $true
if (-not $provider) { exit 1 }
$claudeOk = ($provider.available_modes | Where-Object { $_.id -eq "claude" }).available
$gpt4Ok = ($provider.available_modes | Where-Object { $_.id -eq "gpt4" }).available
if (-not $claudeOk -and -not $gpt4Ok) {
    Write-Host "WARN Claude and GPT-4 unavailable - add ANTHROPIC_API_KEY and OPENAI_API_KEY in Railway Variables, then redeploy."
    Write-Host "      See railway.variables.example in the repo."
    exit 2
}
if ($provider.mode -eq "stub") {
    Write-Host "WARN Active provider is stub - set POE_PROVIDER_MODE=claude (or pick Claude in the UI after keys are set)."
    exit 2
}

$root = Test-Endpoint "/" $false
if (-not $root) { exit 1 }

Write-Host "Public deploy OK. Cloud providers enabled. Pick Claude or GPT-4 in Answer mode and run one Ask."
