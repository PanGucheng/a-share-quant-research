$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$ConfigPath = Join-Path $ProjectRoot "configs/workflow_lightgbm_alpha158_csi500.yaml"
$OutputRoot = Join-Path $ProjectRoot "outputs/mlruns_validated"
$QrunWrapper = Join-Path $ProjectRoot "scripts/qrun_with_project_tmp.py"
$LogPath = Join-Path $ProjectRoot ("logs/qrun_lightgbm_alpha158_csi500_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$TempRoot = Join-Path $ProjectRoot "tmp"

New-Item -ItemType Directory -Force $TempRoot | Out-Null

conda activate qlib_env
[Environment]::SetEnvironmentVariable("TMP", $TempRoot, "Process")
[Environment]::SetEnvironmentVariable("TEMP", $TempRoot, "Process")
[Environment]::SetEnvironmentVariable("TMPDIR", $TempRoot, "Process")
$env:TMP = $TempRoot
$env:TEMP = $TempRoot
$env:TMPDIR = $TempRoot
python -c "import os, tempfile; tempfile.tempdir=os.environ['TMP']; print('python_tempdir', tempfile.gettempdir())"
python $QrunWrapper $ConfigPath -e qlib_baseline_lightgbm_alpha158_csi500 -u $OutputRoot *>&1 | Tee-Object -FilePath $LogPath
if ($LASTEXITCODE -ne 0) {
    throw "qrun failed with exit code $LASTEXITCODE. See log: $LogPath"
}
