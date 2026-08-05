$ErrorActionPreference="Stop"

Write-Host "========================================"
Write-Host " Sarembok Agent Module Repair"
Write-Host "========================================"

$Root="C:\Sarembok_VE"
$Public="$Root\Plugins\SarembokAgent\Source\SarembokAgent\Public"
$Private="$Root\Plugins\SarembokAgent\Source\SarembokAgent\Private"

Write-Host "Repairing SarembokAgent.h"

@'
#pragma once

#include "Modules/ModuleManager.h"

class SAREMBOKAGENT_API FSarembokAgentModule : public IModuleInterface
{

public:

    virtual void StartupModule() override;

    virtual void ShutdownModule() override;

};
'@ | Set-Content "$Public\SarembokAgent.h"


Write-Host "Repairing SarembokAgent.cpp"

@'
#include "SarembokAgent.h"

#include "Modules/ModuleManager.h"


void FSarembokAgentModule::StartupModule()
{
    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Agent Initialized")
    );
}


void FSarembokAgentModule::ShutdownModule()
{
    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Agent Shutdown")
    );
}


IMPLEMENT_MODULE(
    FSarembokAgentModule,
    SarembokAgent
)
'@ | Set-Content "$Private\SarembokAgent.cpp"


Write-Host "Cleaning Unreal intermediates"

Get-ChildItem "$Root\Plugins" -Directory |
ForEach-Object {

    $int="$($_.FullName)\Intermediate"

    if(Test-Path $int)
    {
        Remove-Item $int -Recurse -Force
        Write-Host "Removed $int"
    }

}


Write-Host "Generating project files"

& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\GenerateProjectFiles.bat" `
"$Root\SarembokVE.uproject"


Write-Host "Building"

& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" `
SarembokVEEditor Win64 Development `
-project="$Root\SarembokVE.uproject"


Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Agent Repair Complete"
Write-Host "========================================"