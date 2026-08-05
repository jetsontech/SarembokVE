# ==================================================
# SarembokBridge v0.2 Bootstrap
# Unreal Engine Communication Layer
# ==================================================

$Root="C:\Sarembok_VE"

Write-Host ""
Write-Host "===================================="
Write-Host " SarembokBridge Bootstrap v0.2"
Write-Host "===================================="
Write-Host ""


$PluginRoot="$Root\Plugins\SarembokBridge"


$Folders=@(

"$PluginRoot",
"$PluginRoot\Source\SarembokBridge",
"$PluginRoot\Source\SarembokBridge\Public",
"$PluginRoot\Source\SarembokBridge\Private"

)


foreach($folder in $Folders){

    if(!(Test-Path $folder)){

        New-Item `
        -ItemType Directory `
        -Path $folder `
        -Force | Out-Null

        Write-Host "[DIR] $folder"

    }

}



# ------------------------------------------
# Plugin Descriptor
# ------------------------------------------

$Plugin=@'
{
    "FileVersion":3,
    "Version":2,
    "VersionName":"0.2",
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
'@


Set-Content `
"$PluginRoot\SarembokBridge.uplugin" `
$Plugin



# ------------------------------------------
# Build File
# ------------------------------------------

$Build=@'
using UnrealBuildTool;

public class SarembokBridge : ModuleRules
{
    public SarembokBridge(
        ReadOnlyTargetRules Target
    ) : base(Target)
    {

        PCHUsage =
        PCHUsageMode.UseExplicitOrSharedPCHs;


        PublicDependencyModuleNames.AddRange(
        new string[]
        {
            "Core",
            "CoreUObject",
            "Engine",
            "WebSockets",
            "Json",
            "JsonUtilities"
        });


    }
}
'@


Set-Content `
"$PluginRoot\Source\SarembokBridge\SarembokBridge.Build.cs" `
$Build



# ------------------------------------------
# Header
# ------------------------------------------

$Header=@'
#pragma once

#include "Modules/ModuleManager.h"


class FSarembokBridgeModule :
public IModuleInterface
{

public:

virtual void StartupModule() override;

virtual void ShutdownModule() override;


};
'@


Set-Content `
"$PluginRoot\Source\SarembokBridge\Public\SarembokBridge.h" `
$Header



# ------------------------------------------
# CPP
# ------------------------------------------

$CPP=@'
#include "SarembokBridge.h"

#include "Modules/ModuleManager.h"


void FSarembokBridgeModule::StartupModule()
{

UE_LOG(
LogTemp,
Warning,
TEXT("Sarembok Bridge Initialized")
);

}



void FSarembokBridgeModule::ShutdownModule()
{


}


IMPLEMENT_MODULE(
FSarembokBridgeModule,
SarembokBridge
)
'@


Set-Content `
"$PluginRoot\Source\SarembokBridge\Private\SarembokBridge.cpp" `
$CPP



# ------------------------------------------
# Message Protocol
# ------------------------------------------

$Protocol=@'
{
"events":
[
"CHAT",
"VOICE_START",
"VOICE_END",
"VISION_FRAME",
"FACE_COMMAND",
"GESTURE_COMMAND"
],

"runtime":
"ws://127.0.0.1:9000"
}
'@


Set-Content `
"$Root\Backend\WebSocket\unreal_protocol.json" `
$Protocol



Write-Host ""
Write-Host "===================================="
Write-Host " SarembokBridge Bootstrap Complete"
Write-Host "===================================="