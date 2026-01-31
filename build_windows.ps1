# PowerShell script to create a Windows executable for getsupernovae
# Run this on a Windows machine with Python installed.
# Usage (PowerShell):
#   ./build_windows.ps1

param(
    [string]$Python = "python",
    [string]$VenvDir = ".venv_build"
)

Write-Host "Creating virtual environment in $VenvDir..."
& $Python -m venv $VenvDir
$pip = Join-Path $VenvDir "Scripts\pip.exe"
$pythonExe = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "Upgrading pip and installing requirements..."
& $pip install --upgrade pip
& $pip install -r requirements.txt
& $pip install pyinstaller

Write-Host "Running PyInstaller to build one-file exe (this may take a few minutes)..."
# Use semicolon separator for --add-data on Windows
$addData = @(
    "locales;locales",
    "fonts;fonts",
    "sites.json;."
)

$addDataArgs = $addData | ForEach-Object { "--add-data `"$_`"" } | Out-String
$addDataArgs = $addDataArgs -replace "\r?\n"," "

# Build onefile, windowed (no console). Remove --windowed if you want a console.
& $pythonExe -m PyInstaller --noconfirm --clean --onefile --windowed $addDataArgs getsupernovae.py

Write-Host "Build finished. Check dist\getsupernovae.exe for the built executable."