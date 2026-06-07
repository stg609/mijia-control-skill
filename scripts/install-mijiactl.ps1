param(
  [string]$Repo = "stg609/mijia-control-skill",
  [string]$InstallDir = "$HOME\.mijiactl\bin",
  [string]$AssetName = "mijiactl-windows-x64.exe",
  [switch]$NoPathUpdate
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest"
$asset = $release.assets | Where-Object { $_.name -eq $AssetName } | Select-Object -First 1

if (-not $asset) {
  throw "Release asset '$AssetName' was not found in latest release for $Repo."
}

$target = Join-Path $InstallDir "mijiactl.exe"
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $target

if (-not $NoPathUpdate) {
  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $paths = @()
  if ($userPath) {
    $paths = $userPath -split ";"
  }
  if ($paths -notcontains $InstallDir) {
    $newPath = (($paths + $InstallDir) | Where-Object { $_ }) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    $env:Path = "$env:Path;$InstallDir"
  }
}

& $target doctor
