<#
.SYNOPSIS
    Canonical Sarembok_VE Builder & Management Script
.DESCRIPTION
    Provides unified project automation: build, clean, diagnose, and generate project files.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("Build", "Clean", "Diagnose", "Generate")]
    [string]$Action = "Build",

    [Parameter(Mandatory=$false)]
    [string]$Target = "SarembokVEEditor",

    [Parameter(Mandatory=$false)]
    [string]$Configuration = "Development",

    [Parameter(Mandatory=$false)]
    [string]$Platform = "Win64"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Sarembok_VE"
$UProjectPath = "$ProjectRoot\SarembokVE.uproject"

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
        
        # Root directories
        foreach ($Dir in $TargetDirs) {
            $Path = "$ProjectRoot\$Dir"
            if (Test-Path $Path) {
                Write-Host "Removing $Path" -ForegroundColor Gray
                Remove-Item -Path $Path -Recurse -Force -ErrorAction SilentlyContinue
            }
        }

        # Plugin directories
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
}
