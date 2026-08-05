# ============================================================
# Repair-SarembokBridgeRuntime.ps1
#
# Fixes:
# - SarembokBridge duplicate module definition
# - RuntimeManager include
# - Build.cs dependencies
# - Unreal intermediate cleanup
# - Project regeneration
# - Full rebuild
# ============================================================

$Root = "C:\Sarembok_VE"

Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Bridge Runtime Repair"
Write-Host "========================================"
Write-Host ""


# ------------------------------------------------------------
# Locate Runtime Manager
# ------------------------------------------------------------

Write-Host "[1/6] Locating SarembokRuntimeManager..."

$RuntimeHeader = Get-ChildItem `
    $Root `
    -Recurse `
    -Filter SarembokRuntimeManager.h `
    -ErrorAction SilentlyContinue |
    Select-Object -First 1


if($RuntimeHeader)
{
    Write-Host "Found:"
    Write-Host $RuntimeHeader.FullName
}
else
{
    Write-Host "RuntimeManager header not found."
}



# ------------------------------------------------------------
# Repair SarembokBridge.cpp
# ------------------------------------------------------------

Write-Host ""
Write-Host "[2/6] Repairing SarembokBridge.cpp..."


$BridgeCPP =
Join-Path $Root `
"Plugins\SarembokBridge\Source\SarembokBridge\Private\SarembokBridge.cpp"


$BridgeCPPContent = @'
#include "SarembokBridge.h"

#include "Modules/ModuleManager.h"


void FSarembokBridgeModule::StartupModule()
{

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
-Path $BridgeCPP `
-Value $BridgeCPPContent `
-Encoding UTF8


Write-Host "Fixed SarembokBridge.cpp"



# ------------------------------------------------------------
# Repair SarembokBridgeModule.cpp
# ------------------------------------------------------------

Write-Host ""
Write-Host "[3/6] Repairing SarembokBridgeModule.cpp..."


$BridgeModuleCPP =
Join-Path $Root `
"Plugins\SarembokBridge\Source\SarembokBridge\Private\SarembokBridgeModule.cpp"


if(Test-Path $BridgeModuleCPP)
{

$Content = Get-Content `
$BridgeModuleCPP `
-Raw


if($Content -notmatch "SarembokRuntimeManager.h")
{

$Content =
'#include "SarembokRuntimeManager.h"' +
"`r`n" +
$Content


Set-Content `
-Path $BridgeModuleCPP `
-Value $Content `
-Encoding UTF8

Write-Host "Added RuntimeManager include"

}
else
{
Write-Host "Runtime include already exists"
}

}



# ------------------------------------------------------------
# Update SarembokBridge Build.cs
# ------------------------------------------------------------

Write-Host ""
Write-Host "[4/6] Updating SarembokBridge.Build.cs..."


$BuildCS =
Join-Path $Root `
"Plugins\SarembokBridge\Source\SarembokBridge\SarembokBridge.Build.cs"


if(Test-Path $BuildCS)
{

$Build =
Get-Content `
$BuildCS `
-Raw


foreach($Dependency in @(
    "WebSockets",
    "SarembokRuntime"
))
{

if($Build -notmatch $Dependency)
{

$Build =
$Build.Replace(
'"Engine"',
'"Engine",' + "`r`n" + '                "'+$Dependency+'"'
)

Write-Host "Added dependency:" $Dependency

}

}


Set-Content `
-Path $BuildCS `
-Value $Build `
-Encoding UTF8

}



# ------------------------------------------------------------
# Clean Intermediate
# ------------------------------------------------------------

Write-Host ""
Write-Host "[5/6] Cleaning Intermediate folders..."


Get-ChildItem `
$Root\Plugins `
-Recurse `
-Directory `
-Filter Intermediate |
ForEach-Object {

Remove-Item `
$_.FullName `
-Recurse `
-Force `
-ErrorAction SilentlyContinue

Write-Host "Removed:" $_.FullName

}



# ------------------------------------------------------------
# Regenerate + Build
# ------------------------------------------------------------

Write-Host ""
Write-Host "[6/6] Regenerate and Build..."


$UBT =
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.exe"


& $UBT `
-projectfiles `
-project="$Root\SarembokVE.uproject" `
-game `
-progress



$Build =
"C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat"


& $Build `
SarembokVEEditor `
Win64 `
Development `
-project="$Root\SarembokVE.uproject" `
-progress



Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Bridge Repair Finished"
Write-Host "========================================"