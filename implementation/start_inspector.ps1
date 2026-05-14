$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = (Get-Command python).Source
$Server = Join-Path $Root "mcp_server.py"
$Cache = Join-Path $Root ".npm-cache"

New-Item -ItemType Directory -Force -Path $Cache | Out-Null
$env:NPM_CONFIG_CACHE = $Cache
npx -y @modelcontextprotocol/inspector $Python $Server
