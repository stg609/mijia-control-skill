param(
  [string]$Repo = "stg609/mijia-control-skill",
  [string]$SkillName = "controlling-mijia-smart-home",
  [string]$InstallDir = "$HOME\.mijiactl\bin",
  [string]$DataDir = "$HOME\.config\mijiactl",
  [string[]]$Agents = @("claude-code", "openclaw", "cline", "codex", "cursor", "github-copilot", "kiro-cli", "lingma", "opencode", "qwen-code", "trae-cn", "windsurf"),
  [switch]$PurgeData,
  [switch]$NoPathUpdate,
  [switch]$SkipSkill
)

$ErrorActionPreference = "Stop"

if (-not $SkipSkill) {
  if (Get-Command npx -ErrorAction SilentlyContinue) {
    $removedWithCli = $false
    foreach ($commandName in @("remove", "uninstall")) {
      try {
        $skillArgs = @("skills", $commandName, $Repo, "--skill", $SkillName, "-g", "--agent") + $Agents + @("-y")
        npx @skillArgs
        if ($LASTEXITCODE -eq 0) {
          $removedWithCli = $true
          break
        }
      } catch {
      }
    }
    if (-not $removedWithCli) {
      Write-Warning "Could not remove the Skill automatically with npx skills. Remove '$SkillName' from each agent's skills directory manually."
    }
  } else {
    Write-Warning "npx is not available. Remove '$SkillName' from each agent's skills directory manually."
  }
}

$runtimeUninstaller = Join-Path $PSScriptRoot "scripts\uninstall-mijiactl.ps1"
if (Test-Path $runtimeUninstaller) {
  & $runtimeUninstaller -InstallDir $InstallDir -DataDir $DataDir -PurgeData:$PurgeData -NoPathUpdate:$NoPathUpdate
} else {
  $remote = "https://raw.githubusercontent.com/$Repo/master/scripts/uninstall-mijiactl.ps1"
  & ([ScriptBlock]::Create((Invoke-RestMethod -Uri $remote))) -InstallDir $InstallDir -DataDir $DataDir -PurgeData:$PurgeData -NoPathUpdate:$NoPathUpdate
}
