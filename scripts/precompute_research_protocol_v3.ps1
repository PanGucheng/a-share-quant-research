param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$Python = 'E:\anaconda_envs\qlib_env\python.exe',
    [switch]$Preflight
)
$ErrorActionPreference = 'Stop'
if ($RunId -notmatch '^v3_precompute_[A-Za-z0-9_-]+$') { throw 'Use a v3_precompute_ run-id.' }
$taskRoot = Split-Path -Parent $PSScriptRoot
Push-Location $taskRoot
try {
    if ($Preflight) {
        & $Python scripts/precompute_research_protocol_v3.py --run-id $RunId --preflight
        if ($LASTEXITCODE -ne 0) { throw 'V3 metadata preflight failed.' }
        return
    }
    New-Item -ItemType Directory -Path 'tmp' -Force | Out-Null
    foreach ($taskPool in @('Broad494', 'Strict332')) {
        foreach ($taskStage in @('precompute', 'replay')) {
            $taskScript = if ($taskStage -eq 'precompute') {
                'scripts/precompute_research_protocol_v3.py'
            } else { 'scripts/replay_research_protocol_v3_predictions.py' }
            $taskLog = "tmp/$RunId-$taskPool-$taskStage.log"
            # PowerShell 5.1 treats native stderr as ErrorRecord; retain warnings
            # in the log and use the native exit code as the failure authority.
            $ErrorActionPreference = 'Continue'
            try {
                & $Python -u $taskScript --run-id $RunId --pool $taskPool 2>&1 |
                    ForEach-Object { "$PSItem" } | Tee-Object -FilePath $taskLog -Append
                $taskExit = $LASTEXITCODE
            } finally { $ErrorActionPreference = 'Stop' }
            if ($taskExit -ne 0) {
                throw "$taskPool $taskStage failed. Preserve outputs; inspect $taskLog."
            }
        }
    }
    Write-Output 'Both pools: nine models and independent prediction replay complete. No outcome evaluation.'
} finally { Pop-Location }
