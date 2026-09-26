param(
  [string]$Python = "python"
)
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $PSScriptRoot
& $Python -m pip install --upgrade pyinstaller
& $Python -m PyInstaller --noconfirm --clean --onefile --windowed --name "LondonProjectGPT" ".\LondonProjectGPT.py"
Write-Host "Built: $PSScriptRoot\dist\LondonProjectGPT.exe"
Write-Host "Set LONDON_PROJECT_ROOT to the local repo if auto-discovery cannot find it."
