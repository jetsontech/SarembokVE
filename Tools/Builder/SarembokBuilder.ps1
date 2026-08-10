<#
.SYNOPSIS
    Canonical Sarembok_VE Builder & Management Script
.DESCRIPTION
    Provides unified project automation: build, clean, diagnose, generate project files, and create production releases.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("Build", "Clean", "Diagnose", "Generate", "Production")]
    [string]$Action = "Build",

    [Parameter(Mandatory=$false)]
    [string]$Target = "SarembokVEEditor",

    [Parameter(Mandatory=$false)]
    [string]$Configuration = "Development",

    [Parameter(Mandatory=$false)]
    [string]$Platform = "Win64",

    [Parameter(Mandatory=$false)]
    [switch]$Production
)

$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Sarembok_VE"
$UProjectPath = "$ProjectRoot\SarembokVE.uproject"

if ($Production) {
    $Action = "Production"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Sarembok Builder CLI (Action: $Action)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Locate Unreal Engine 5.8 Build.bat
function Get-UEBuildBat {
    $UEBat = Get-ChildItem "C:\Program Files\Epic Games", "D:\Program Files\Epic Games", "C:\Epic Games" -Recurse -Filter "Build.bat" -ErrorAction SilentlyContinue | 
        Where-Object { $_.FullName -match "UE_5" } | 
        Select-Object -First 1
    
    if (-not $UEBat) {
        throw "Unreal Engine Build.bat not found in standard Epic Games paths."
    }
    return $UEBat.FullName
}

switch ($Action) {
    "Diagnose" {
        $DiagScript = "$ProjectRoot\Tools\Diagnostics\Test-SarembokProject.ps1"
        if (Test-Path $DiagScript) {
            & powershell -ExecutionPolicy Bypass -File $DiagScript
        } else {
            throw "Diagnostic script not found at $DiagScript"
        }
    }

    "Clean" {
        Write-Host "Cleaning generated directories..." -ForegroundColor Yellow
        $TargetDirs = @("Binaries", "Intermediate", ".vs", "Saved", "DerivedDataCache")
        
        foreach ($Dir in $TargetDirs) {
            $Path = "$ProjectRoot\$Dir"
            if (Test-Path $Path) {
                Write-Host "Removing $Path" -ForegroundColor Gray
                Remove-Item -Path $Path -Recurse -Force -ErrorAction SilentlyContinue
            }
        }

        $Plugins = Get-ChildItem "$ProjectRoot\Plugins" -Directory
        foreach ($Plugin in $Plugins) {
            foreach ($Dir in @("Binaries", "Intermediate")) {
                $Path = "$($Plugin.FullName)\$Dir"
                if (Test-Path $Path) {
                    Write-Host "Removing $Path" -ForegroundColor Gray
                    Remove-Item -Path $Path -Recurse -Force -ErrorAction SilentlyContinue
                }
            }
        }
        Write-Host "Clean complete." -ForegroundColor Green
    }

    "Generate" {
        $BuildBat = Get-UEBuildBat
        Write-Host "Generating Unreal project files using UBT..." -ForegroundColor Yellow
        & $BuildBat -projectfiles -project="$UProjectPath" -game -engine
        Write-Host "Project files generated successfully." -ForegroundColor Green
    }

    "Build" {
        $BuildBat = Get-UEBuildBat
        Write-Host "Executing build: Target=$Target | Platform=$Platform | Config=$Configuration" -ForegroundColor Yellow
        Write-Host "Using Build.bat: $BuildBat`n" -ForegroundColor Gray

        & $BuildBat $Target $Platform $Configuration "$UProjectPath" -NoLiveCoding -NoXGE -NoUBA
        Write-Host "`nBuild completed successfully!" -ForegroundColor Green
    }

    "Production" {
        Write-Host "[1/5] Validating environment & dependencies..." -ForegroundColor Yellow
        $BuildBat = Get-UEBuildBat
        
        Write-Host "[2/5] Executing target build (SarembokVEEditor)..." -ForegroundColor Yellow
        & $BuildBat "SarembokVEEditor" $Platform $Configuration "$UProjectPath" -NoLiveCoding -NoXGE -NoUBA

        Write-Host "[3/5] Generating production configuration..." -ForegroundColor Yellow
        $ProdConfigPath = "$ProjectRoot\Config\sarembok.production.json"
        $ProdConfig = @{
            version = "3.0.0"
            environment = "production"
            websocketPort = 9000
            governance = @{
                riskThreshold = 0.65
                confidenceFloor = 0.65
                hardRiskCeiling = 0.90
            }
            resilience = @{
                walEnabled = $true
                autoReconnect = $true
            }
        } | ConvertTo-Json -Depth 4
        Set-Content -Path $ProdConfigPath -Value $ProdConfig

        Write-Host "[4/5] Staging distribution bundle..." -ForegroundColor Yellow
        $StagingDir = "$ProjectRoot\Saved\Staging\SarembokVE-Production-v3.0.0"
        if (Test-Path $StagingDir) { Remove-Item -Path $StagingDir -Recurse -Force }
        New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null

        Copy-Item -Path "$ProjectRoot\SarembokVE.uproject" -Destination $StagingDir
        Copy-Item -Path "$ProjectRoot\Plugins" -Destination $StagingDir -Recurse
        Copy-Item -Path "$ProjectRoot\Config" -Destination $StagingDir -Recurse
        Copy-Item -Path "$ProjectRoot\backend" -Destination $StagingDir -Recurse
        Copy-Item -Path "$ProjectRoot\frontend" -Destination $StagingDir -Recurse
        Copy-Item -Path "$ProjectRoot\Tools" -Destination $StagingDir -Recurse

        Write-Host "[5/5] Production staging release created at $StagingDir" -ForegroundColor Green
        Write-Host "`n========================================================" -ForegroundColor Green
        Write-Host "  SAREMBOK VE PRODUCTION EDITION BUNDLE STAGED CLEANLY " -ForegroundColor Green
        Write-Host "========================================================" -ForegroundColor Green
    }
}
