param(
    [string]$RunId = 'v3_recompute_audit_20260909_v1',
    [ValidateRange(1, 4)][int]$Workers = 2,
    [string]$Python = 'E:\anaconda_envs\qlib_env\python.exe'
)

# New-run recomputation only. Never copy, delete, or rewrite prior receipts.
if ($RunId -notmatch '^v3_recompute_[A-Za-z0-9_-]+$') {
    throw 'Use an independent v3_recompute_ run-id.'
}
$taskRoot = Split-Path -Parent $PSScriptRoot
Push-Location $taskRoot
try {
    New-Item -ItemType Directory -Path 'tmp' -Force | Out-Null
    function Invoke-V3Stage {
        param([string]$Name, [string[]]$Arguments)
        & $Python -u @Arguments 2>&1 | Tee-Object -FilePath "tmp/$RunId-$Name.log" -Append
        if ($LASTEXITCODE -ne 0) {
            throw "V3 stage $Name failed (exit $LASTEXITCODE). Preserve outputs and inspect the log."
        }
    }
    Invoke-V3Stage -Name 'probe' -Arguments @(
        'scripts/revalidate_research_protocol_v3.py', '--run-id', $RunId, '--mode', 'probe')
    Invoke-V3Stage -Name 'p0-p2' -Arguments @(
        'scripts/run_research_protocol_v3_mvp.py', '--run-id', $RunId, '--stage', 'all', '--workers', "$Workers")
    foreach ($taskFold in @('annual_2015', 'annual_2023')) {
        Invoke-V3Stage -Name $taskFold -Arguments @(
            'scripts/run_research_protocol_v3_mvp.py', '--run-id', $RunId,
            '--stage', 'wide-canary', '--wide-fold', $taskFold)
    }
    Invoke-V3Stage -Name 'verify' -Arguments @(
        'scripts/revalidate_research_protocol_v3.py', '--run-id', $RunId, '--mode', 'verify')
    Write-Output 'Recomputation and count checks finished. Research/resource approval remains pending review.'
} finally {
    Pop-Location
}
