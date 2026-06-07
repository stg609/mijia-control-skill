param(
  [string]$RepoUrl = "git+https://github.com/stg609/mijia-control-skill.git",
  [string]$SkillSource = "stg609/mijia-control-skill",
  [string]$SkillName = "controlling-mijia-smart-home",
  [switch]$Login
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  throw "uv is required. Install uv first: https://docs.astral.sh/uv/"
}

if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
  throw "npx is required to install the agent Skill. Install Node.js first: https://nodejs.org/"
}

npx skills add $SkillSource --skill $SkillName -g -y
uv tool install "mijiactl[mijia] @ $RepoUrl"

$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$canonical = Join-Path $source "skills\$SkillName"

if (Test-Path $canonical) {
  $skillRoot = Join-Path $HOME ".codex\skills"
  $target = Join-Path $skillRoot $SkillName
  New-Item -ItemType Directory -Force -Path $target | Out-Null
  Copy-Item -Recurse -Force (Join-Path $canonical "*") $target
}

mijiactl config init

if ($Login) {
  mijiactl login
}

mijiactl doctor
