param(
  [string]$InstallDir = "$HOME\.mijiactl\bin",
  [string]$DataDir = "$HOME\.config\mijiactl",
  [switch]$PurgeData,
  [switch]$NoPathUpdate
)

$ErrorActionPreference = "Stop"

$removed = @()
$kept = @()

$target = Join-Path $InstallDir "mijiactl.exe"
if (Test-Path $target) {
  Remove-Item -LiteralPath $target -Force
  $removed += $target
}

if (Test-Path $InstallDir) {
  $remaining = Get-ChildItem -LiteralPath $InstallDir -Force -ErrorAction SilentlyContinue
  if (-not $remaining) {
    Remove-Item -LiteralPath $InstallDir -Force
    $removed += $InstallDir
  }
}

$parentInstallDir = Split-Path -Parent $InstallDir
if ($parentInstallDir -and (Test-Path $parentInstallDir)) {
  $remainingParent = Get-ChildItem -LiteralPath $parentInstallDir -Force -ErrorAction SilentlyContinue
  if (-not $remainingParent) {
    Remove-Item -LiteralPath $parentInstallDir -Force
    $removed += $parentInstallDir
  }
}

if (-not $NoPathUpdate) {
  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  if ($userPath) {
    $paths = $userPath -split ";" | Where-Object { $_ -and ($_ -ne $InstallDir) }
    [Environment]::SetEnvironmentVariable("Path", ($paths -join ";"), "User")
  }
}

if ($PurgeData) {
  if (Test-Path $DataDir) {
    Remove-Item -LiteralPath $DataDir -Recurse -Force
    $removed += $DataDir
  }
} else {
  if (Test-Path $DataDir) {
    $kept += $DataDir
  }
}

[PSCustomObject]@{
  ok = $true
  removed = $removed
  kept = $kept
  note = if ($PurgeData) { "Runtime, config, auth, capability cache, and snapshot cache removed." } else { "Runtime removed. Auth, config, and caches kept. Rerun with -PurgeData to remove them." }
} | ConvertTo-Json -Depth 4
