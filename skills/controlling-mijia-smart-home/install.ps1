param(
  [string]$RepoUrl = "git+https://github.com/stg609/mijia-control-skill.git",
  [string]$SkillSource = "stg609/mijia-control-skill",
  [switch]$Login
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  throw "uv is required. Install uv first: https://docs.astral.sh/uv/"
}

if (Get-Command npx -ErrorAction SilentlyContinue) {
  npx skills add $SkillSource --skill controlling-mijia-smart-home -g -y
}

uv tool install "mijiactl[mijia] @ $RepoUrl"
mijiactl config init

if ($Login) {
  mijiactl login
}

mijiactl doctor
