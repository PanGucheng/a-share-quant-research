$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $ProjectRoot

$PythonExe = if ($env:QLIB_ENV_PYTHON) { $env:QLIB_ENV_PYTHON } else { "E:\anaconda_envs\qlib_env\python.exe" }
& $PythonExe -m data_quality.checker @args
