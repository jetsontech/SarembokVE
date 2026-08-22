<#
.SYNOPSIS
    Sarembok VE - Unreal Engine 5.8 MetaHuman Launcher
.DESCRIPTION
    Launches Unreal Engine 5.8 with SarembokVE.uproject and prepares the C++ Bridge.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\SarembokVE"
Set-Location $ProjectRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "     SAREMBOK VE - UNREAL ENGINE 5.8 METAHUMAN LAUNCHER  " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$EditorPath = "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$ProjectFile = "$ProjectRoot\SarembokVE.uproject"

if (Test-Path $EditorPath) {
    Write-Host "`n[OK] Unreal Engine 5.8 detected." -ForegroundColor Green
    Write-Host "[OK] Project: $ProjectFile" -ForegroundColor Green
    Write-Host "`n[INFO] Starting Unreal Editor 5.8 in background..." -ForegroundColor Yellow
    Start-Process -FilePath $EditorPath -ArgumentList "`"$ProjectFile`""
    Write-Host "`n[SUCCESS] Unreal Editor is booting. Press Play (Alt+P) in the level to activate the live MetaHuman C++ Bridge." -ForegroundColor Cyan
} else {
    Write-Host "`n[ERROR] Unreal Engine 5.8 executable not found at: $EditorPath" -ForegroundColor Red
}
