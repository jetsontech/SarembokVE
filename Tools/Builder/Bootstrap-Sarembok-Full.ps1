# ==============================================
# Sarembok VE Full Bootstrap v1.0
# Unreal Engine 5.8
# ==============================================

$ErrorActionPreference = "Stop"

$ROOT = "C:\Sarembok_VE"
$PLUGIN = "$ROOT\Plugins\SarembokBridge"
$SOURCE = "$PLUGIN\Source\SarembokBridge"

$UE = "C:\Program Files\Epic Games\UE_5.8"
$UBT = "$UE\Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.exe"
$EDITOR = "$UE\Engine\Binaries\Win64\UnrealEditor.exe"

Write-Host ""
Write-Host "====================================="
Write-Host " Sarembok VE Full Bootstrap v1.0"
Write-Host "====================================="
Write-Host ""


# ------------------------------
# Create directories
# ------------------------------

$dirs = @(
    "$ROOT\AI\Runtime\state",
    "$ROOT\Logs",
    "$ROOT\Content\Avatar",
    "$PLUGIN",
    "$SOURCE"
)

foreach($d in $dirs)
{
    if(!(Test-Path $d))
    {
        New-Item -ItemType Directory -Path $d | Out-Null
    }

    Write-Host "[DIR] $d"
}


# ------------------------------
# Plugin descriptor
# ------------------------------

@'
{
    "FileVersion":3,
    "Version":1,
    "VersionName":"0.1",
    "FriendlyName":"Sarembok Bridge",
    "Description":"AI Digital Human Communication Bridge",
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
'@ | Out-File "$PLUGIN\SarembokBridge.uplugin" -Encoding utf8


# ------------------------------
# Build.cs
# ------------------------------

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
                "Engine"
            }
        );
    }
}
'@ | Out-File "$SOURCE\SarembokBridge.Build.cs" -Encoding utf8



# ------------------------------
# Module Header
# ------------------------------

@'
#pragma once

#include "Modules/ModuleManager.h"

class FSarembokBridgeModule :
    public IModuleInterface
{

public:

    virtual void StartupModule() override;

    virtual void ShutdownModule() override;

};
'@ | Out-File "$SOURCE\Public\SarembokBridgeModule.h" -Encoding utf8



# ------------------------------
# Runtime Manager Header
# ------------------------------

@'
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "SarembokRuntimeManager.generated.h"


UCLASS()
class SAREMBOKBRIDGE_API USarembokRuntimeManager :
public UObject
{

GENERATED_BODY()

public:

void InitializeRuntime();

void SendAIMessage(
const FString& Message
);

};
'@ | Out-File "$SOURCE\Public\SarembokRuntimeManager.h" -Encoding utf8



# ------------------------------
# Runtime Manager CPP
# ------------------------------

@'
#include "SarembokRuntimeManager.h"


void USarembokRuntimeManager::InitializeRuntime()
{

UE_LOG(
LogTemp,
Display,
TEXT("Sarembok AI Runtime Online")
);

}



void USarembokRuntimeManager::SendAIMessage(
const FString& Message
)
{

UE_LOG(
LogTemp,
Display,
TEXT("AI Message: %s"),
*Message
);

}
'@ | Out-File "$SOURCE\Private\SarembokRuntimeManager.cpp" -Encoding utf8



# ------------------------------
# Module CPP
# ------------------------------

@'
#include "SarembokBridgeModule.h"
#include "SarembokRuntimeManager.h"


void FSarembokBridgeModule::StartupModule()
{

UE_LOG(
LogTemp,
Display,
TEXT("Sarembok Bridge Initialized")
);


USarembokRuntimeManager* Runtime =
NewObject<USarembokRuntimeManager>();

Runtime->InitializeRuntime();

}



void FSarembokBridgeModule::ShutdownModule()
{

UE_LOG(
LogTemp,
Display,
TEXT("Sarembok Bridge Shutdown")
);

}


IMPLEMENT_MODULE(
FSarembokBridgeModule,
SarembokBridge
)
'@ | Out-File "$SOURCE\Private\SarembokBridgeModule.cpp" -Encoding utf8



# ------------------------------
# Enable Plugin in Project
# ------------------------------

$uproject="$ROOT\SarembokVE.uproject"

if(Test-Path $uproject)
{

$json = Get-Content $uproject -Raw | ConvertFrom-Json


if(!$json.Plugins)
{
    $json | Add-Member Plugins @()
}


$exists=$json.Plugins |
Where-Object {$_.Name -eq "SarembokBridge"}


if(!$exists)
{

$json.Plugins += @{
    Name="SarembokBridge"
    Enabled=$true
}

}


$json |
ConvertTo-Json -Depth 20 |
Out-File $uproject -Encoding utf8


Write-Host "[PROJECT] Plugin Enabled"

}



# ------------------------------
# Generate Project Files
# ------------------------------

Write-Host ""
Write-Host "[BUILD] Generating Unreal Project Files"

& "$UE\Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.exe" `
-projectfiles `
-project="$uproject" `
-game `
-progress



# ------------------------------
# Compile
# ------------------------------

Write-Host ""
Write-Host "[BUILD] Compiling Sarembok VE"


& $UBT `
SarembokVEEditor `
Win64 `
Development `
-project="$uproject" `
-progress



# ------------------------------
# Launch
# ------------------------------

Write-Host ""
Write-Host "[START] Launching Unreal"


Start-Process `
$EDITOR `
"$uproject"


Write-Host ""
Write-Host "====================================="
Write-Host " Sarembok VE Bootstrap COMPLETE"
Write-Host "====================================="
