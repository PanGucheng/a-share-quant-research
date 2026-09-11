param([string]$Python = 'E:\anaconda_envs\qlib_env\python.exe')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
& $Python -m pytest -q tests/test_economic_prediction_structure.py
if ($LASTEXITCODE -ne 0) { throw 'E1 synthetic checks failed' }
& $Python -X utf8 scripts/study_economic_e1.py
if ($LASTEXITCODE -ne 0) { throw 'E1 run failed; preserve failure evidence' }
& $Python -X utf8 scripts/study_economic_e1.py --verify
if ($LASTEXITCODE -ne 0) { throw 'E1 independent replay failed' }
Write-Host 'E1 COMPLETE / PREDICTION STRUCTURE VERIFIED. E3/E4 NOT AUTHORIZED.'
