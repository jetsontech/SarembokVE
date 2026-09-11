<#
.SYNOPSIS
    Launches the Sarembok Multi-Agent Voice Orchestrator Gateway (Port 8765).
#>
param(
    [int]$Port = 8765,
    [string]$Database = "sarembok_runtime.db"
)

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  SAREMBOK VE // MULTI-AGENT VOICE ORCHESTRATOR & BARGE-IN GATEWAY" -ForegroundColor Green
Write-Host "  Port: $Port | Ledger: $Database (SQLite-WAL)" -ForegroundColor DarkCyan
Push-Location $PSScriptRoot
try {
    python Runtime/sarembok_voice_orchestrator.py $Port
}
finally {
    Pop-Location
}
