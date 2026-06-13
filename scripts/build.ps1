param(
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$modeArgs = @()
if ($OneFile) {
    $modeArgs += "--onefile"
} else {
    $modeArgs += "--onedir"
}

python -m PyInstaller `
    --name SKHU_PC_Management `
    --windowed `
    --uac-admin `
    --clean `
    --noconfirm `
    --paths "$projectRoot\src" `
    --add-data "$projectRoot\resources;resources" `
    @modeArgs `
    "$projectRoot\src\skhu_pc_management\main.py"
