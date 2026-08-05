Write-Host "========================================"
Write-Host " Sarembok Bridge Header Final Fix"
Write-Host "========================================"

$Root="C:\Sarembok_VE"
$Bridge="$Root\Plugins\SarembokBridge\Source\SarembokBridge"

$Public="$Bridge\Public"
$Private="$Bridge\Private"

New-Item -ItemType Directory -Force $Public | Out-Null
New-Item -ItemType Directory -Force $Private | Out-Null


Write-Host "Creating SarembokBridge.h"

@'
#pragma once

#include "CoreMinimal.h"

class SAREMBOKBRIDGE_API FSarembokBridge
{

public:

    void Initialize();

};
'@ | Out-File "$Public\SarembokBridge.h" -Encoding utf8


Write-Host "Repairing SarembokBridge.cpp"

@'
#include "SarembokBridge.h"

void FSarembokBridge::Initialize()
{
    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Bridge Runtime Initialized")
    );
}
'@ | Out-File "$Private\SarembokBridge.cpp" -Encoding utf8



Write-Host "Cleaning cache"

$Remove=@(
"$Root\Intermediate",
"$Root\Saved",
"$Bridge\Intermediate"
)

foreach($Path in $Remove)
{
    if(Test-Path $Path)
    {
        Remove-Item $Path -Recurse -Force
        Write-Host "Removed $Path"
    }
}


Write-Host "Generating project files"

& "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.exe" `
 -projectfiles `
 -project="$Root\SarembokVE.uproject" `
 -game `
 -progress


Write-Host "Building SarembokVE"

& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" `
 SarembokVEEditor `
 Win64 `
 Development `
 "-Project=$Root\SarembokVE.uproject"


Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Bridge Header Fix Complete"
Write-Host "========================================"