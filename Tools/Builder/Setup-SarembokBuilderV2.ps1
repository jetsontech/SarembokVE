# ==========================================================
# Sarembok Builder v2 Setup
# Creates Builder system + templates
# ==========================================================

$ErrorActionPreference = "Stop"

$BUILDER = "C:\Sarembok_VE\Tools\Builder"
$TEMPLATE = "$BUILDER\Templates\Bridge"


Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Builder v2 Setup"
Write-Host "========================================"
Write-Host ""


# Create folders

New-Item -ItemType Directory `
    -Force `
    -Path $TEMPLATE | Out-Null


# ----------------------------------------------------------
# SarembokBridge.Build.cs
# ----------------------------------------------------------

@'
using UnrealBuildTool;

public class SarembokBridge : ModuleRules
{
    public SarembokBridge(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "CoreUObject",
                "Engine",
                "Projects",
                "Sockets",
                "Networking"
            }
        );
    }
}
'@ | Out-File `
"$TEMPLATE\SarembokBridge.Build.cs" `
-Encoding utf8



# ----------------------------------------------------------
# Plugin descriptor
# ----------------------------------------------------------

@'
{
    "FileVersion": 3,
    "Version": 1,
    "VersionName": "2.0",
    "FriendlyName": "Sarembok Bridge",
    "Description": "Sarembok Digital Human Platform Runtime Bridge",
    "Category": "Sarembok",
    "Modules":
    [
        {
            "Name": "SarembokBridge",
            "Type": "Runtime",
            "LoadingPhase": "Default"
        }
    ]
}
'@ | Out-File `
"$TEMPLATE\SarembokBridge.uplugin" `
-Encoding utf8



# ----------------------------------------------------------
# Runtime Manager Header
# ----------------------------------------------------------

@'
#pragma once

#include "CoreMinimal.h"

class SAREMBOKBRIDGE_API FSarembokRuntimeManager
{

public:

    static FSarembokRuntimeManager& Get();

    void Initialize();

    void Shutdown();


private:

    FSarembokRuntimeManager();

};
'@ | Out-File `
"$TEMPLATE\SarembokRuntimeManager.h" `
-Encoding utf8



# ----------------------------------------------------------
# Runtime Manager CPP
# ----------------------------------------------------------

@'
#include "SarembokRuntimeManager.h"


FSarembokRuntimeManager::FSarembokRuntimeManager()
{
}


FSarembokRuntimeManager& FSarembokRuntimeManager::Get()
{
    static FSarembokRuntimeManager Instance;

    return Instance;
}


void FSarembokRuntimeManager::Initialize()
{
    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Runtime Manager Initialized")
    );
}


void FSarembokRuntimeManager::Shutdown()
{
}
'@ | Out-File `
"$TEMPLATE\SarembokRuntimeManager.cpp" `
-Encoding utf8



Write-Host ""
Write-Host "Templates created."
Write-Host ""


# Run generator

Set-Location $BUILDER


if (Test-Path ".\SarembokBuilder.ps1")
{

    Write-Host "Running Sarembok Builder..."

    .\SarembokBuilder.ps1 -Create Bridge

}
else
{
    Write-Host "ERROR: SarembokBuilder.ps1 not found."
    Write-Host "Place this file inside Tools\Builder."
}


Write-Host ""
Write-Host "========================================"
Write-Host " Builder v2 Setup Complete"
Write-Host "========================================"