param(
  [string]$OutDir = "dist\release"
)

$ErrorActionPreference = "Stop"

uv run --extra mijia --with pyinstaller pyinstaller --onefile --clean --name mijiactl mijiactl\__main__.py

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Copy-Item -Force "dist\mijiactl.exe" (Join-Path $OutDir "mijiactl-windows-x64.exe")

Write-Output (Join-Path $OutDir "mijiactl-windows-x64.exe")
