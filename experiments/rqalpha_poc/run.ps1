param(
    [string]$Python = 'E:\qlib_prj\rqalpha_poc_env\Scripts\python.exe',
    [string]$MainRoot = 'E:\qlib_prj\qlib_baseline'
)
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
if ($taskRoot -eq (Resolve-Path -LiteralPath $MainRoot).Path) { throw 'Run only in isolated worktree' }
Set-Location -LiteralPath $taskRoot
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
& $Python -c "import sys, rqalpha; assert sys.prefix != sys.base_prefix; assert 'qlib_env' not in sys.prefix; assert rqalpha.__version__ == '6.4.0'"
if ($LASTEXITCODE -ne 0) { throw 'Expected isolated RQAlpha 6.4.0 environment' }
& $Python -m experiments.rqalpha_poc.verify_inputs --main-root $MainRoot
if ($LASTEXITCODE -ne 0) { throw 'Input/active-run isolation check failed' }
$taskOutput = Join-Path $taskRoot ('outputs\rqalpha_poc\' + [guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $taskOutput | Out-Null
$env:RQALPHA_POC_RESULT = Join-Path $taskOutput 'results.json'
try {
    & $Python -m pytest experiments/rqalpha_poc -q --tb=short
    if ($LASTEXITCODE -ne 0) { throw "PoC failed; retained $taskOutput" }
} finally {
    Remove-Item Env:RQALPHA_POC_RESULT -ErrorAction SilentlyContinue
}
Write-Output "Bounded PoC complete: $taskOutput; production migration remains pending."
