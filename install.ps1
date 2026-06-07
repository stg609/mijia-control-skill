param(
  [string]$Repo = "stg609/mijia-control-skill",
  [string]$SkillName = "controlling-mijia-smart-home",
  [string]$InstallDir = "$HOME\.mijiactl\bin",
  [string[]]$Agents = @("claude-code", "openclaw", "cline", "codex", "cursor", "github-copilot", "kiro-cli", "lingma", "opencode", "qwen-code", "trae-cn", "windsurf"),
  [switch]$UseSourceRuntime,
  [switch]$Login
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
  throw "npx is required to install the agent Skill. Install Node.js first: https://nodejs.org/"
}

$skillArgs = @("skills", "add", $Repo, "--skill", $SkillName, "-g", "--agent") + $Agents + @("-y")
npx @skillArgs

if ($UseSourceRuntime) {
  if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required for source runtime installs. Install uv first: https://docs.astral.sh/uv/"
  }
  uv tool install "mijiactl[mijia] @ git+https://github.com/$Repo.git"
} else {
  $installer = "https://raw.githubusercontent.com/$Repo/main/scripts/install-mijiactl.ps1"
  & ([ScriptBlock]::Create((Invoke-RestMethod -Uri $installer))) -Repo $Repo -InstallDir $InstallDir
}

mijiactl config init

if ($Login) {
  mijiactl login
}

mijiactl doctor
