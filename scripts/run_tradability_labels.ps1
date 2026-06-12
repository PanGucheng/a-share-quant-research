param(
    [string]$Config = "tradability/config.yaml",
    [string]$ProviderUri = "",
    [string]$Market = "",
    [string]$StartTime = "",
    [string]$EndTime = "",
    [string]$DataQualityDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$PythonExe = if ($env:QLIB_ENV_PYTHON) { $env:QLIB_ENV_PYTHON } else { "E:\anaconda_envs\qlib_env\python.exe" }

$argsList = @("-m", "tradability.runner", "--config", $Config)
if ($ProviderUri) { $argsList += @("--provider-uri", $ProviderUri) }
if ($Market) { $argsList += @("--market", $Market) }
if ($StartTime) { $argsList += @("--start-time", $StartTime) }
if ($EndTime) { $argsList += @("--end-time", $EndTime) }
if ($DataQualityDir) { $argsList += @("--data-quality-dir", $DataQualityDir) }
if ($OutputDir) { $argsList += @("--output-dir", $OutputDir) }

Push-Location $ProjectRoot
try {
    & $PythonExe $argsList
}
finally {
    Pop-Location
}
