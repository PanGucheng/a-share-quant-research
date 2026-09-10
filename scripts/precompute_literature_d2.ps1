param(
    [string]$Python = 'E:\anaconda_envs\qlib_env\python.exe',
    [string]$RunId = 'd2_rch_20260910_v1',
    [switch]$Preflight,
    [switch]$CanaryOnly
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
function Invoke-D2([string[]]$JobArguments) {
    & $Python -u scripts/precompute_literature_d2.py @JobArguments --run-id $RunId
    if ($LASTEXITCODE -ne 0) { throw "D2 stopped: $($JobArguments -join ' ')" }
}
Invoke-D2 @('preflight')
if ($Preflight) { return }
Invoke-D2 @('cache')
Invoke-D2 @('fit', '--arm', 'H', '--fold', 'annual_2023')
Invoke-D2 @('replay', '--arm', 'H', '--fold', 'annual_2023')
if ($CanaryOnly) { return }
foreach ($Arm in @('R', 'C', 'H')) {
    Invoke-D2 @('fit', '--arm', $Arm)
    Invoke-D2 @('replay', '--arm', $Arm)
}
Invoke-D2 @('seal')
