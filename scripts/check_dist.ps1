param(
    [string]$DistPath = ".\dist\SKHU_PC_Management"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$resolvedDist = if ([System.IO.Path]::IsPathRooted($DistPath)) {
    $DistPath
} else {
    Join-Path $projectRoot $DistPath
}

$requiredPaths = @(
    "SKHU_PC_Management.exe",
    "_internal",
    "README_RELEASE.txt"
)

$missing = @()
foreach ($relativePath in $requiredPaths) {
    $candidate = Join-Path $resolvedDist $relativePath
    if (-not (Test-Path $candidate)) {
        $missing += $relativePath
    }
}

if ($missing.Count -gt 0) {
    Write-Host "배포본 필수 파일 누락:" -ForegroundColor Red
    foreach ($item in $missing) {
        Write-Host " - $item" -ForegroundColor Red
    }
    exit 1
}

$resourceRoots = @(
    (Join-Path $resolvedDist "resources"),
    (Join-Path $resolvedDist "_internal\resources")
)
$resourcesRoot = $null
foreach ($candidate in $resourceRoots) {
    if (Test-Path $candidate) {
        $resourcesRoot = $candidate
        break
    }
}

if ($null -eq $resourcesRoot) {
    Write-Host "배포본 resources 폴더를 찾지 못했습니다. 확인 위치:" -ForegroundColor Red
    foreach ($candidate in $resourceRoots) {
        Write-Host " - $candidate" -ForegroundColor Red
    }
    exit 1
}

$resourceRequiredPaths = @(
    "images\skhu_logo.ico",
    "TaskBar.reg"
)
foreach ($relativePath in $resourceRequiredPaths) {
    $candidate = Join-Path $resourcesRoot $relativePath
    if (-not (Test-Path $candidate)) {
        Write-Host "배포본 resources 필수 파일 누락: $relativePath" -ForegroundColor Red
        exit 1
    }
}

$shortcutPath = Join-Path $resourcesRoot "TaskBar"
$shortcuts = @()
if (Test-Path $shortcutPath) {
    $shortcuts = @(Get-ChildItem -Path $shortcutPath -Filter "*.lnk" -File)
}

Write-Host "배포본 필수 파일 확인 완료: $resolvedDist" -ForegroundColor Green
Write-Host "resources 위치: $resourcesRoot" -ForegroundColor Green
if ($shortcuts.Count -eq 0) {
    Write-Host "주의: resources\TaskBar\*.lnk 파일이 없습니다. 작업표시줄 리소스 검증은 경고를 표시합니다." -ForegroundColor Yellow
} else {
    Write-Host "작업표시줄 바로가기 $($shortcuts.Count)개 확인" -ForegroundColor Green
}
