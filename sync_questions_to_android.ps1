$base = $PSScriptRoot
$src = Join-Path $base "questions.csv"
$dstDir = Join-Path $base "ExamMasterAndroid\app\src\main\assets"
$dst = Join-Path $dstDir "questions.csv"

if (-not (Test-Path $src)) {
    Write-Error "Source not found: $src"
    exit 1
}

if (-not (Test-Path $dstDir)) {
    New-Item -ItemType Directory -Path $dstDir | Out-Null
}

Copy-Item -Path $src -Destination $dst -Force
Write-Host "Copied $src -> $dst"