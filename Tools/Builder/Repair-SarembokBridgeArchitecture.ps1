$Root="C:\Sarembok_VE"

Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Bridge Architecture Repair"
Write-Host "========================================"


$Bridge="$Root\Plugins\SarembokBridge\Source\SarembokBridge"
$Public="$Bridge\Public"
$Private="$Bridge\Private"


#
# Fix SarembokBridge.h
#

Write-Host "Repairing SarembokBridge.h"

@'
#pragma once

#include "Modules/ModuleManager.h"

class FSarembokBridgeModule : public IModuleInterface
{

public:

    virtual void StartupModule() override;

    virtual void ShutdownModule() override;

};

'@ | Set-Content "$Public\SarembokBridge.h"



#
# Fix Module cpp
#

Write-Host "Repairing SarembokBridgeModule.cpp"

@'
#include "SarembokBridge.h"
#include "SarembokRuntimeManager.h"

#include "UObject/UObjectGlobals.h"


void FSarembokBridgeModule::StartupModule()
{

    USarembokRuntimeManager* Runtime =
        NewObject<USarembokRuntimeManager>();

    Runtime->AddToRoot();

    Runtime->InitializeRuntime();

}



void FSarembokBridgeModule::ShutdownModule()
{


}


IMPLEMENT_MODULE(
    FSarembokBridgeModule,
    SarembokBridge
)

'@ | Set-Content "$Private\SarembokBridgeModule.cpp"



#
# Fix Runtime Manager cpp
#

Write-Host "Repairing RuntimeManager.cpp"


@'
#include "SarembokRuntimeManager.h"


void USarembokRuntimeManager::InitializeRuntime()
{

    UE_LOG(
        LogTemp,
        Warning,
        TEXT("Sarembok Runtime Manager Initialized")
    );

}

'@ | Set-Content "$Private\SarembokRuntimeManager.cpp"



#
# Remove stale bridge files
#

if(Test-Path "$Private\SarembokBridge.cpp")
{
    Remove-Item "$Private\SarembokBridge.cpp" -Force
}



#
# Clean
#

Write-Host "Cleaning Unreal cache"


Remove-Item "$Root\Intermediate" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$Root\Saved" -Recurse -Force -ErrorAction SilentlyContinue


Get-ChildItem "$Root\Plugins" -Directory |
ForEach-Object {

    $p="$($_.FullName)\Intermediate"

    if(Test-Path $p)
    {
        Remove-Item $p -Recurse -Force
    }

}



#
# Build
#

Write-Host ""
Write-Host "Building..."

& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" `
SarembokVEEditor `
Win64 `
Development `
-project="$Root\SarembokVE.uproject" `
-progress



Write-Host ""
Write-Host "========================================"
Write-Host " Bridge Architecture Repair Complete"
Write-Host "========================================"