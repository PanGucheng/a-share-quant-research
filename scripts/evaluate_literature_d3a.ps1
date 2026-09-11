param(
    [string]$Python = 'E:\anaconda_envs\qlib_env\python.exe',
    [switch]$Preflight,
    [string]$RunId = 'd3a_five_arm_20260911_v1'
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $repoPath
try {
    if ($Preflight) {
        & $Python scripts/evaluate_literature_d3a.py preflight --run-id $RunId
        if ($LASTEXITCODE -ne 0) { throw 'D3-A preflight failed.' }
    } else {
        $logDir = Join-Path $repoPath 'outputs/literature_factor_representation_d3a_logs'
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        $logFile = Join-Path $logDir ((Get-Date -Format 'yyyyMMdd_HHmmss_fffffff') + '.log')
        & $Python scripts/evaluate_literature_d3a.py run --run-id $RunId 2>&1 | Tee-Object -FilePath $logFile
        if ($LASTEXITCODE -ne 0) { throw "D3-A failed; preserve opening receipts and incomplete output. Log: $logFile" }
    }
} finally {
    Pop-Location
}
