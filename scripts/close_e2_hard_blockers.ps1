param(
    [ValidateSet('Validate', 'Quotes', 'States', 'Dividends')]
    [string]$Phase = 'Validate'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$researchPython = 'E:\anaconda_envs\qlib_env\python.exe'
if (-not (Test-Path -LiteralPath $researchPython)) { throw 'Configured qlib Python is missing.' }
Push-Location -LiteralPath $repoRoot
try {
    if ($Phase -eq 'Validate') {
        & $researchPython -m pytest -q tests/test_e2_hard_closure.py tests/test_economic_readiness_closure.py tests/test_economic_data_boundary.py tests/test_economic_execution_contract.py tests/test_economic_qlib_runtime.py
    } else {
        & $researchPython scripts/scan_e2_hard_history.py $Phase.ToLowerInvariant()
    }
    if ($LASTEXITCODE -ne 0) { throw "E2 phase failed with exit code $LASTEXITCODE; preserve outputs and inspect." }
} finally {
    Pop-Location
}
