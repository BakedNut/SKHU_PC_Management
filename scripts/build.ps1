param(
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$hiddenImportArgs = @()
$hiddenImports = @(
    "wmi",
    "win32com",
    "win32com.client",
    "pythoncom",
    "pywintypes"
)
$localProductKeysPath = Join-Path $projectRoot "src\skhu_pc_management\infrastructure\license\local_product_keys.py"
if (Test-Path $localProductKeysPath) {
    $hiddenImports += "skhu_pc_management.infrastructure.license.local_product_keys"
}
foreach ($hiddenImport in $hiddenImports) {
    $hiddenImportArgs += "--hidden-import"
    $hiddenImportArgs += $hiddenImport
}

function Copy-ReleaseReadme {
    param(
        [string]$TargetDirectory
    )

    $releaseReadme = Join-Path $projectRoot "packaging\README_RELEASE.txt"
    if (Test-Path $releaseReadme) {
        New-Item -ItemType Directory -Force -Path $TargetDirectory | Out-Null
        Copy-Item -Path $releaseReadme -Destination (Join-Path $TargetDirectory "README_RELEASE.txt") -Force
    }
}

if ($OneFile) {
    python -m PyInstaller `
        --name SKHU_PC_Management `
        --onefile `
        --windowed `
        --uac-admin `
        --clean `
        --noconfirm `
        --paths "$projectRoot\src" `
        --add-data "$projectRoot\resources;resources" `
        @hiddenImportArgs `
        "$projectRoot\src\skhu_pc_management\main.py"
    Copy-ReleaseReadme -TargetDirectory (Join-Path $projectRoot "dist")
} else {
    python -m PyInstaller `
        --clean `
        --noconfirm `
        "$projectRoot\SKHU_PC_Management.spec"
    Copy-ReleaseReadme -TargetDirectory (Join-Path $projectRoot "dist\SKHU_PC_Management")
}
