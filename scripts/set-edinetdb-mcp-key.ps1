<#
.SYNOPSIS
    Register EDINET DB MCP API Key as user environment variable.

.DESCRIPTION
    Sets EDINETDB_AUTH env var to "Bearer <ApiKey>" format.
    Codex CLI references this via config.toml env_http_headers.
    Does NOT affect local DB (ai_project.db) settings.

.PARAMETER ApiKey
    API Key string from EDINET DB MCP service.

.EXAMPLE
    .\set-edinetdb-mcp-key.ps1 -ApiKey "your-api-key-here"

.NOTES
    Open a NEW terminal after running this script.
#>

param(
    [Parameter(Mandatory=$true, HelpMessage="Enter EDINET DB MCP API Key")]
    [string]$ApiKey
)

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    Write-Error "API Key is empty."
    exit 1
}

$authValue = "Bearer $ApiKey"

[Environment]::SetEnvironmentVariable(
    "EDINETDB_AUTH",
    $authValue,
    "User"
)

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " EDINETDB_AUTH saved to user environment variable." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Variable: EDINETDB_AUTH"
Write-Host "  Value:    Bearer ***$(($ApiKey).Substring([Math]::Max(0, $ApiKey.Length - 4)))"
Write-Host "  Scope:    User"
Write-Host ""
Write-Host "[IMPORTANT] Open a NEW terminal, then start codex." -ForegroundColor Yellow
Write-Host ""

$env:EDINETDB_AUTH = $authValue
Write-Host "(Also applied to current session)"
