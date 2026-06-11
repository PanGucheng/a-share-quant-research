param(
    [string]$SourceProvider = "E:\qlib_prj\qlib_data\cn_data_community_20260609",
    [string]$OutputProvider = "E:\qlib_prj\qlib_data\cn_data_community_20260609_derived",
    [string]$UniverseSource = "E:\qlib_prj\qlib_baseline\outputs\universes\community_20260609\all_stock_shsz.txt",
    [string]$UniverseName = "all_stock_shsz",
    [string]$LogPath = "E:\qlib_prj\qlib_baseline\outputs\reports\derived_provider_community_20260609.md"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourceProvider)) {
    throw "Source provider does not exist: $SourceProvider"
}
if (-not (Test-Path -LiteralPath $UniverseSource)) {
    throw "Universe source does not exist: $UniverseSource"
}
if (Test-Path -LiteralPath $OutputProvider) {
    throw "Output provider already exists: $OutputProvider"
}

$OutputParent = Split-Path -Parent $OutputProvider
New-Item -ItemType Directory -Force $OutputParent | Out-Null

Copy-Item -LiteralPath $SourceProvider -Destination $OutputProvider -Recurse -Force

$OutputInstruments = Join-Path $OutputProvider "instruments"
New-Item -ItemType Directory -Force $OutputInstruments | Out-Null
$UniverseTarget = Join-Path $OutputInstruments "$UniverseName.txt"
Copy-Item -LiteralPath $UniverseSource -Destination $UniverseTarget -Force

$UniverseRows = (Get-Content -LiteralPath $UniverseTarget | Where-Object { $_.Trim() }).Count
$ForbiddenRows = (
    Select-String -Path $UniverseTarget -Pattern "^(BJ|SH000|SZ399)" -ErrorAction SilentlyContinue |
    Measure-Object
).Count

$Log = @(
    "# Derived Provider Build",
    "",
    "- Source provider: ``$SourceProvider``",
    "- Output provider: ``$OutputProvider``",
    "- Universe source: ``$UniverseSource``",
    "- Universe target: ``$UniverseTarget``",
    "- Universe rows: ``$UniverseRows``",
    "- Forbidden prefix rows: ``$ForbiddenRows``",
    "- Built at: ``$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")``"
)

$LogDir = Split-Path -Parent $LogPath
New-Item -ItemType Directory -Force $LogDir | Out-Null
$Log | Set-Content -LiteralPath $LogPath -Encoding UTF8

if ($ForbiddenRows -ne 0) {
    throw "Derived universe contains forbidden BJ/SH000/SZ399 rows: $ForbiddenRows"
}

Write-Host "Built derived provider: $OutputProvider"
