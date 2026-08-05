# ==========================================================
# Sarembok Builder v3
# Digital Human Module Factory
# ==========================================================

$ErrorActionPreference="Stop"


$ROOT="C:\Sarembok_VE"
$BUILDER="$ROOT\Tools\Builder"
$TEMPLATES="$BUILDER\Templates"


Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Builder v3"
Write-Host " Module Factory Upgrade"
Write-Host "========================================"
Write-Host ""


# ----------------------------------------------------------
# Create module templates
# ----------------------------------------------------------

$MODULES=@(
"Avatar",
"Voice",
"Vision",
"Agent",
"Memory"
)


foreach($module in $MODULES)
{

$path="$TEMPLATES\$module"


New-Item `
-Type Directory `
-Force `
-Path "$path\Public" | Out-Null


New-Item `
-Type Directory `
-Force `
-Path "$path\Private" | Out-Null


@"
using UnrealBuildTool;

public class Sarembok$module : ModuleRules
{
    public Sarembok$module(ReadOnlyTargetRules Target)
        : base(Target)
    {
        PCHUsage =
        PCHUsageMode.UseExplicitOrSharedPCHs;


        PublicDependencyModuleNames.AddRange(
        new string[]
        {
            "Core",
            "CoreUObject",
            "Engine"
        });
    }
}
"@ |
Out-File `
"$path\Sarembok$module.Build.cs" `
-Encoding utf8



@"
{
    "FileVersion":3,
    "Version":1,
    "VersionName":"1.0",
    "FriendlyName":"Sarembok $module",
    "Category":"Sarembok",

    "Modules":
    [
        {
            "Name":"Sarembok$module",
            "Type":"Runtime",
            "LoadingPhase":"Default"
        }
    ]
}
"@ |
Out-File `
"$path\Sarembok$module.uplugin" `
-Encoding utf8



@"
#pragma once

#include "CoreMinimal.h"

class SAREMBOK${module}_API FSarembok${module}
{

public:

    void Initialize();

};
"@ |
Out-File `
"$path\Public\Sarembok$module.h" `
-Encoding utf8



@"
#include "Sarembok$module.h"


void FSarembok$module::Initialize()
{

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok $module Initialized")
    );

}
"@ |
Out-File `
"$path\Private\Sarembok$module.cpp" `
-Encoding utf8

}


# ----------------------------------------------------------
# Add factory function
# ----------------------------------------------------------

$BUILDERFILE="$BUILDER\SarembokBuilder.ps1"

$content=Get-Content $BUILDERFILE -Raw


if($content -notmatch "Create-Module")
{

$content += @'




function Create-Module($Name)
{

    Write-Host ""
    Write-Host "Creating Sarembok $Name module..."
    

    $MODULE_ROOT =
    Join-Path $PLUGINS "Sarembok$Name"


    New-Item `
    -ItemType Directory `
    -Force `
    -Path "$MODULE_ROOT\Source\Sarembok$Name\Public" | Out-Null


    New-Item `
    -ItemType Directory `
    -Force `
    -Path "$MODULE_ROOT\Source\Sarembok$Name\Private" | Out-Null



    Copy-Item `
    "$TEMPLATES\$Name\Sarembok$Name.Build.cs" `
    "$MODULE_ROOT\Source\Sarembok$Name\Sarembok$Name.Build.cs" `
    -Force


    Copy-Item `
    "$TEMPLATES\$Name\Public\*" `
    "$MODULE_ROOT\Source\Sarembok$Name\Public" `
    -Force


    Copy-Item `
    "$TEMPLATES\$Name\Private\*" `
    "$MODULE_ROOT\Source\Sarembok$Name\Private" `
    -Force


    Copy-Item `
    "$TEMPLATES\$Name\Sarembok$Name.uplugin" `
    "$MODULE_ROOT\Sarembok$Name.uplugin" `
    -Force


    Write-Host ""
    Write-Host "Sarembok $Name created."

}

'@


Set-Content `
$BUILDERFILE `
$content

}



# ----------------------------------------------------------
# Update parameter options
# ----------------------------------------------------------

Write-Host ""
Write-Host "Adding module support..."



Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Builder v3 COMPLETE"
Write-Host "========================================"