$Root = "C:\Sarembok_VE"

Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Runtime Final Repair"
Write-Host "========================================"
Write-Host ""

$Bridge = "$Root\Plugins\SarembokBridge\Source\SarembokBridge"
$Public = "$Bridge\Public"
$Private = "$Bridge\Private"

#
# 1. Locate Runtime Manager
#

$runtime = Get-ChildItem `
"$Root\Plugins" `
-Recurse `
-Filter "SarembokRuntimeManager.h" |
Select-Object -First 1

if(!$runtime)
{
    throw "SarembokRuntimeManager.h not found"
}

Write-Host "Found Runtime:"
Write-Host $runtime.FullName


#
# 2. Ensure RuntimeManager is a UObject
#

$header = Get-Content $runtime.FullName -Raw

if($header -notmatch "UCLASS")
{
    Write-Host "Repairing RuntimeManager as UObject..."

@'
#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "SarembokRuntimeManager.generated.h"

UCLASS()
class SAREMBOKBRIDGE_API USarembokRuntimeManager : public UObject
{
    GENERATED_BODY()

public:

    void InitializeRuntime();

};

'@ | Set-Content $runtime.FullName

}


#
# 3. Repair Bridge Module
#

$module = "$Private\SarembokBridgeModule.cpp"

Write-Host "Repairing Bridge Module..."

@'
#include "SarembokBridge.h"
#include "SarembokRuntimeManager.h"

#include "Modules/ModuleManager.h"
#include "UObject/UObjectGlobals.h"


class FSarembokBridgeModule : public IModuleInterface
{

public:

virtual void StartupModule() override
{

    USarembokRuntimeManager* Runtime =
        NewObject<USarembokRuntimeManager>();

    Runtime->AddToRoot();

    Runtime->InitializeRuntime();

}


virtual void ShutdownModule() override
{


}


};


IMPLEMENT_MODULE(
    FSarembokBridgeModule,
    SarembokBridge
)

'@ | Set-Content $module


#
# 4. Remove duplicate implementation
#

$old = "$Private\SarembokBridge.cpp"

if(Test-Path $old)
{

Write-Host "Removing duplicate module implementation"

Remove-Item $old -Force

}


#
# 5. Clean Unreal
#

Write-Host ""
Write-Host "Cleaning Unreal intermediates..."

Remove-Item "$Root\Intermediate" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$Root\Saved" -Recurse -Force -ErrorAction SilentlyContinue

Get-ChildItem "$Root\Plugins" -Directory |
ForEach-Object {

$int = Join-Path $_.FullName "Intermediate"

if(Test-Path $int)
{
Remove-Item $int -Recurse -Force
}

}


#
# 6. Regenerate
#

Write-Host ""
Write-Host "Generating project files..."

& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\GenerateProjectFiles.bat" `
-project="$Root\SarembokVE.uproject"


#
# 7. Build
#

Write-Host ""
Write-Host "Building SarembokVE..."

& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" `
SarembokVEEditor `
Win64 `
Development `
-project="$Root\SarembokVE.uproject" `
-progress


Write-Host ""
Write-Host "========================================"
Write-Host " Runtime Repair Finished"
Write-Host "========================================"