param(
  [string]$Repo = "stg609/mijia-control-skill",
  [string]$InstallDir = "$HOME\.mijiactl\bin",
  [string]$AssetName = "mijiactl-windows-x64.exe",
  [switch]$NoPathUpdate
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

try {
  $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest"
} catch {
  throw @"
Failed to query the latest GitHub Release for $Repo.

Manual install:
1. Open https://github.com/$Repo/releases/latest
2. Download mijiactl-windows-x64.exe
3. Rename it to mijiactl.exe
4. Put it in $InstallDir
5. Add $InstallDir to your user Path

Original error: $($_.Exception.Message)
"@
}

$asset = $release.assets | Where-Object { $_.name -eq $AssetName } | Select-Object -First 1

if (-not $asset) {
  throw "Release asset '$AssetName' was not found. Open https://github.com/$Repo/releases/latest and check the published assets."
}

$target = Join-Path $InstallDir "mijiactl.exe"
$downloadError = $null
try {
  Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $target -UseBasicParsing
} catch {
  $downloadError = $_.Exception.Message
  try {
    Add-Type -AssemblyName System.Net.Http
    $client = [System.Net.Http.HttpClient]::new()
    try {
      $client.DefaultRequestHeaders.UserAgent.ParseAdd("mijiactl-installer")
      $bytes = $client.GetByteArrayAsync($asset.browser_download_url).GetAwaiter().GetResult()
      [System.IO.File]::WriteAllBytes($target, $bytes)
    } finally {
      $client.Dispose()
    }
  } catch {
    throw @"
Failed to download '$AssetName'.

Tried:
1. Invoke-WebRequest -OutFile
2. .NET HttpClient byte download

Manual install:
1. Open https://github.com/$Repo/releases/latest
2. Download $AssetName
3. Rename it to mijiactl.exe
4. Save it as $target
5. Open a new PowerShell window and run: mijiactl doctor

Invoke-WebRequest error: $downloadError
HttpClient error: $($_.Exception.Message)
"@
  }
}

if (-not (Test-Path $target) -or (Get-Item $target).Length -eq 0) {
  throw "Downloaded '$AssetName' but '$target' is missing or empty. Open https://github.com/$Repo/releases/latest and install it manually."
}

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
