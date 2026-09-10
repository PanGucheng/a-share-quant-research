[CmdletBinding()]
param(
    [string]$Python = 'E:\anaconda_envs\qlib_env\python.exe',
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$')]
    [string]$RunId = 'd1_structure_20260910_v2'
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Python executable does not exist: $Python"
}
$D1Repository = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $D1Repository
try {
    & $Python 'scripts/run_literature_representation_d1.py' check
    if ($LASTEXITCODE -ne 0) { throw "D1 packet check failed: $LASTEXITCODE" }
    & $Python 'scripts/run_literature_representation_d1.py' full --run-id $RunId
    if ($LASTEXITCODE -ne 0) { throw "D1 structural scan/replay failed: $LASTEXITCODE" }
    & $Python 'scripts/run_literature_representation_d1.py' verify-full --run-id $RunId
    if ($LASTEXITCODE -ne 0) { throw "D1 receipt/aggregate verification failed: $LASTEXITCODE" }
    Write-Host 'D1 structure and independent oracle replay finished. Policy review is still required; D2 is not authorized.'
}
finally {
    Pop-Location
}
