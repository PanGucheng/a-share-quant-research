param(
    [ValidateSet('Preflight', 'Run', 'Replay', 'Evaluate')][string]$Action = 'Preflight',
    [string]$RunId = 'lgbm_nested_20260916_v1',
    [string]$Python = 'E:\anaconda_envs\qlib_env\python.exe'
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
function Invoke-Checked([string[]]$CommandArgs) {
    & $Python @CommandArgs
    if ($LASTEXITCODE -ne 0) { throw "LightGBM research failed. Preserve outputs; later phases were not started." }
}
if ($Action -eq 'Preflight') {
    Invoke-Checked @('scripts/research_lightgbm.py', 'preflight', '--run-id', $RunId)
} elseif ($Action -eq 'Run') {
    Invoke-Checked @('-m', 'pytest', '-q', 'tests/test_lightgbm_nested.py')
    Invoke-Checked @('scripts/research_lightgbm.py', 'run', '--run-id', $RunId)
    Invoke-Checked @('scripts/research_lightgbm.py', 'replay', '--run-id', $RunId)
    Invoke-Checked @('scripts/evaluate_lightgbm.py', '--run-id', $RunId)
} elseif ($Action -eq 'Replay') {
    Invoke-Checked @('scripts/research_lightgbm.py', 'replay', '--run-id', $RunId)
} else {
    Invoke-Checked @('scripts/evaluate_lightgbm.py', '--run-id', $RunId)
}
