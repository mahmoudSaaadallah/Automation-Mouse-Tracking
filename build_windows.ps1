$ErrorActionPreference = "Stop"

Write-Host "Installing build dependency (PyInstaller)..."
python -m pip install --upgrade pyinstaller

Write-Host "Building EXE..."
python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name MouseTrackerReplay `
  --collect-submodules pynput `
  main.py

Write-Host ""
Write-Host "Build done."
Write-Host "Output: dist\\MouseTrackerReplay.exe"
