param(
    [switch]$SafeMode,
    [string]$ConfigPath
)

$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$ConfigName = if ($SafeMode) { "workflow_lightgbm_alpha158_csi500_sandbox.yaml" } else { "workflow_lightgbm_alpha158_csi500.yaml" }
if (-not $ConfigPath) {
    $ConfigPath = Join-Path $ProjectRoot (Join-Path "configs" $ConfigName)
}
$ConfigStem = [System.IO.Path]::GetFileNameWithoutExtension($ConfigPath)
$ExperimentName = "qlib_baseline_$ConfigStem"
$OutputRoot = Join-Path $ProjectRoot "outputs/mlruns_validated"
$QrunWrapper = Join-Path $ProjectRoot "scripts/qrun_with_project_tmp.py"
$LogPath = Join-Path $ProjectRoot ("logs/qrun_{0}_{1}.log" -f $ConfigStem, (Get-Date -Format "yyyyMMdd_HHmmss"))
$TempRoot = Join-Path $ProjectRoot "tmp"

New-Item -ItemType Directory -Force $TempRoot | Out-Null

$PythonExe = if ($env:QLIB_ENV_PYTHON) { $env:QLIB_ENV_PYTHON } else { "E:\anaconda_envs\qlib_env\python.exe" }
[Environment]::SetEnvironmentVariable("TMP", $TempRoot, "Process")
[Environment]::SetEnvironmentVariable("TEMP", $TempRoot, "Process")
[Environment]::SetEnvironmentVariable("TMPDIR", $TempRoot, "Process")
$env:TMP = $TempRoot
$env:TEMP = $TempRoot
$env:TMPDIR = $TempRoot
if ($SafeMode) {
    $env:QLIB_BASELINE_SAFE_MODE = "1"
} else {
    Remove-Item Env:\QLIB_BASELINE_SAFE_MODE -ErrorAction SilentlyContinue
}
& $PythonExe -c "import os, tempfile; tempfile.tempdir=os.environ['TMP']; print('python_tempdir', tempfile.gettempdir())"
& $PythonExe $QrunWrapper $ConfigPath -e $ExperimentName -u $OutputRoot *>&1 | Tee-Object -FilePath $LogPath
if ($LASTEXITCODE -ne 0) {
    throw "qrun failed with exit code $LASTEXITCODE. See log: $LogPath"
}
