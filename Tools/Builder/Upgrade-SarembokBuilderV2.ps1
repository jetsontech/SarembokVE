# ==========================================================
# Sarembok Builder v2 Full Upgrade
# One-shot setup + generation
# ==========================================================

$ErrorActionPreference = "Stop"


$ROOT = "C:\Sarembok_VE"
$BUILDER = "$ROOT\Tools\Builder"
$TEMPLATES = "$BUILDER\Templates\Bridge"

$PLUGIN = "$ROOT\Plugins\SarembokBridge"


Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Builder v2 Full Upgrade"
Write-Host "========================================"
Write-Host ""


# ----------------------------------------------------------
# Create directories
# ----------------------------------------------------------

New-Item `
-Type Directory `
-Force `
-Path $TEMPLATES | Out-Null


# ----------------------------------------------------------
# Build.cs Template
# ----------------------------------------------------------

@'
using UnrealBuildTool;

public class SarembokBridge : ModuleRules
{
    public SarembokBridge(ReadOnlyTargetRules Target)
        : base(Target)
    {
        PCHUsage =
            PCHUsageMode.UseExplicitOrSharedPCHs;


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
"$TEMPLATES\SarembokBridge.Build.cs" `
-Encoding utf8



# ----------------------------------------------------------
# Plugin Template
# ----------------------------------------------------------

@'
{
    "FileVersion":3,
    "Version":1,
    "VersionName":"2.0",
    "FriendlyName":"Sarembok Bridge",
    "Description":"Sarembok Digital Human Runtime Bridge",
    "Category":"Sarembok",

    "Modules":
    [
        {
            "Name":"SarembokBridge",
            "Type":"Runtime",
            "LoadingPhase":"Default"
        }
    ]
}
'@ | Out-File `
"$TEMPLATES\SarembokBridge.uplugin" `
-Encoding utf8



# ----------------------------------------------------------
# Module CPP
# ----------------------------------------------------------

@'
#include "Modules/ModuleManager.h"


class FSarembokBridgeModule :
    public IModuleInterface
{

public:

    virtual void StartupModule() override
    {
        UE_LOG(
            LogTemp,
            Display,
            TEXT("Sarembok Bridge Initialized")
        );
    }


    virtual void ShutdownModule() override
    {
        UE_LOG(
            LogTemp,
            Display,
            TEXT("Sarembok Bridge Shutdown")
        );
    }

};


IMPLEMENT_MODULE(
    FSarembokBridgeModule,
    SarembokBridge
)
'@ | Out-File `
"$TEMPLATES\SarembokBridge.cpp" `
-Encoding utf8



# ----------------------------------------------------------
# Runtime Header
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
"$TEMPLATES\SarembokRuntimeManager.h" `
-Encoding utf8



# ----------------------------------------------------------
# Runtime CPP
# ----------------------------------------------------------

@'
#include "SarembokRuntimeManager.h"


FSarembokRuntimeManager::
FSarembokRuntimeManager()
{
}



FSarembokRuntimeManager&
FSarembokRuntimeManager::Get()
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
"$TEMPLATES\SarembokRuntimeManager.cpp" `
-Encoding utf8



# ----------------------------------------------------------
# Patch Builder
# ----------------------------------------------------------

$BUILDERFILE="$BUILDER\SarembokBuilder.ps1"


$content = Get-Content $BUILDERFILE -Raw


if ($content -notmatch "SarembokBridge.cpp")
{

$patch = @'

    Write-Template `
        "$TEMPLATES\Bridge\SarembokBridge.cpp" `
        "$PLUGIN_ROOT\Source\SarembokBridge\Private\SarembokBridge.cpp"

'@


$content=$content.Replace(
'Write-Template `
        "$TEMPLATES\Bridge\SarembokBridge.uplugin"',
$patch+
'    Write-Template `
        "$TEMPLATES\Bridge\SarembokBridge.uplugin"'
)


Set-Content `
$BUILDERFILE `
$content

}


# ----------------------------------------------------------
# Run Builder
# ----------------------------------------------------------

Set-Location $BUILDER


Write-Host ""
Write-Host "Generating SarembokBridge..."
Write-Host ""


.\SarembokBuilder.ps1 -Create Bridge



# ----------------------------------------------------------
# Verify
# ----------------------------------------------------------

Write-Host ""
Write-Host "Checking generated files..."
Write-Host ""


$FILES=@(

"$PLUGIN\Source\SarembokBridge\SarembokBridge.Build.cs",

"$PLUGIN\Source\SarembokBridge\Public\SarembokRuntimeManager.h",

"$PLUGIN\Source\SarembokBridge\Private\SarembokRuntimeManager.cpp",

"$PLUGIN\Source\SarembokBridge\Private\SarembokBridge.cpp",

"$PLUGIN\SarembokBridge.uplugin"

)


foreach($file in $FILES)
{
    if(Test-Path $file)
    {
        Write-Host "[OK] $file"
    }
    else
    {
        Write-Host "[MISSING] $file"
    }
}



# ----------------------------------------------------------
# Generate Unreal files
# ----------------------------------------------------------

Write-Host ""
Write-Host "Generating Unreal project files..."
Write-Host ""


$UE="C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\GenerateProjectFiles.bat"


if(Test-Path $UE)
{

    & $UE "$ROOT\SarembokVE.uproject"

}
else
{
    Write-Host "Unreal Engine 5.8 build tools not found."
}


Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Builder v2 COMPLETE"
Write-Host "========================================"