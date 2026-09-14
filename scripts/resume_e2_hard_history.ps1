param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('States', 'Dividends')]
    [string]$Phase,
    [ValidateRange(0, 20)]
    [int]$MaxRetries = 8,
    [ValidateRange(1, 600)]
    [int]$RetryDelaySeconds = 30,
    [ValidateRange(1, 600)]
    [int]$MaxDelaySeconds = 120
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$researchPython = 'E:\anaconda_envs\qlib_env\python.exe'
Push-Location -LiteralPath $repoRoot
try {
    & $researchPython -u scripts/retry_e2_hard_history.py $Phase.ToLowerInvariant() --max-retries $MaxRetries --retry-delay $RetryDelaySeconds --max-delay $MaxDelaySeconds
    if ($LASTEXITCODE -ne 0) { throw "E2 $Phase interrupted; preserve outputs and inspect source status." }
} finally {
    Pop-Location
}
