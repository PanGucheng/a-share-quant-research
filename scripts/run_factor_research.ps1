param(
    [string]$ProviderUri = "E:/qlib_prj/qlib_data/cn_data_community_20260609_derived",
    [string]$Market = "csi500",
    [string]$StartTime = "2017-01-01",
    [string]$EndTime = "2020-08-01",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
if (-not $OutputDir) {
    $OutputDir = Join-Path $ProjectRoot ("outputs/factor_research/{0}_{1}_{2}" -f $Market, $StartTime, $EndTime)
}

$PythonExe = if ($env:QLIB_ENV_PYTHON) { $env:QLIB_ENV_PYTHON } else { "E:\anaconda_envs\qlib_env\python.exe" }
& $PythonExe -m factor_research.runner `
    --provider-uri $ProviderUri `
    --market $Market `
    --start-time $StartTime `
    --end-time $EndTime `
    --output-dir $OutputDir
