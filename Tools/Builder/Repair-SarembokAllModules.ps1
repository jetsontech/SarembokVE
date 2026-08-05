# ============================================
# Sarembok VE - Complete Module Architecture Repair
# Repairs all plugin module startup architecture
# ============================================

$Root = "C:\Sarembok_VE"
$Plugins = "$Root\Plugins"

Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok VE Complete Module Repair"
Write-Host "========================================"
Write-Host ""

$Modules = @(
    "SarembokAgent",
    "SarembokAvatar",
    "SarembokBridge",
    "SarembokMemory",
    "SarembokVision",
    "SarembokVoice"
)

foreach ($Module in $Modules)
{
    Write-Host ""
    Write-Host "Repairing $Module..."

    $Base = "$Plugins\$Module\Source\$Module"

    $Public = "$Base\Public"
    $Private = "$Base\Private"

    if (!(Test-Path $Public))
    {
        New-Item -ItemType Directory -Path $Public -Force | Out-Null
    }

    if (!(Test-Path $Private))
    {
        New-Item -ItemType Directory -Path $Private -Force | Out-Null
    }


    #
    # Header
    #

    @"
#pragma once

#include "Modules/ModuleManager.h"

class F${Module} : public IModuleInterface
{

public:

    virtual void StartupModule() override;

    virtual void ShutdownModule() override;

};
"@ | Out-File "$Public\$Module.h" -Encoding utf8


    #
    # CPP
    #

    @"
#include "$Module.h"

void F${Module}::StartupModule()
{

    UE_LOG(
        LogTemp,
        Display,
        TEXT("$Module Initialized")
    );

}


void F${Module}::ShutdownModule()
{

    UE_LOG(
        LogTemp,
        Display,
        TEXT("$Module Shutdown")
    );

}


IMPLEMENT_MODULE(
    F${Module},
    $Module
)
"@ | Out-File "$Private\$Module.cpp" -Encoding utf8


    #
    # Remove old bad runtime manager files if they exist
    #

    $OldRuntime = "$Private\SarembokRuntimeManager.cpp"

    if(Test-Path $OldRuntime)
    {
        Write-Host "Removing obsolete RuntimeManager implementation"
        Remove-Item $OldRuntime -Force
    }

}



# ============================================
# Clean Unreal cache
# ============================================

Write-Host ""
Write-Host "Cleaning Unreal intermediates..."

$CleanPaths = @(
    "$Root\Intermediate",
    "$Root\Saved",
    "$Plugins\SarembokAgent\Intermediate",
    "$Plugins\SarembokAvatar\Intermediate",
    "$Plugins\SarembokBridge\Intermediate",
    "$Plugins\SarembokMemory\Intermediate",
    "$Plugins\SarembokVision\Intermediate",
    "$Plugins\SarembokVoice\Intermediate"
)

foreach($Path in $CleanPaths)
{
    if(Test-Path $Path)
    {
        Remove-Item $Path -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Removed $Path"
    }
}



# ============================================
# Generate project files
# ============================================

Write-Host ""
Write-Host "Generating Unreal project files..."

$UBT = "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.exe"

& $UBT `
-projectfiles `
-project="$Root\SarembokVE.uproject" `
-game `
-progress



# ============================================
# Build
# ============================================

Write-Host ""
Write-Host "Building SarembokVE..."

& $UBT `
SarembokVEEditor `
Win64 `
Development `
-project="$Root\SarembokVE.uproject" `
-progress



Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok VE Repair Complete"
Write-Host "========================================"