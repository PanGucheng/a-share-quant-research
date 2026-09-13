param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('States', 'Dividends')]
    [string]$Phase
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$researchPython = 'E:\anaconda_envs\qlib_env\python.exe'
Push-Location -LiteralPath $repoRoot
try {
    & $researchPython -u scripts/resume_e2_hard_history.py $Phase.ToLowerInvariant()
    if ($LASTEXITCODE -ne 0) { throw "E2 $Phase interrupted; preserve outputs and inspect source status." }
} finally {
    Pop-Location
}
