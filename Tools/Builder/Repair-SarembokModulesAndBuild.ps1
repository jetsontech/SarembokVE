# ============================================================
# Repair-SarembokModulesAndBuild.ps1
#
# Sarembok VE Unreal Module Repair Utility
#
# Fixes:
# - Unreal API macro naming
# - SarembokBridge include order
# - WebSockets dependency
# - Intermediate cleanup
# - Project regeneration
# - Build validation
# ============================================================

$ProjectRoot = "C:\Sarembok_VE"

$PluginsRoot = Join-Path $ProjectRoot "Plugins"

Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Module Repair Utility"
Write-Host "========================================"
Write-Host ""


# ------------------------------------------------------------
# Fix Unreal API Macros
# ------------------------------------------------------------

Write-Host "[1/5] Repairing Unreal API macros..."

$MacroFixes = @{
    "SAREMBOKAvatar_API" = "SAREMBOKAVATAR_API"
    "SAREMBOKMemory_API" = "SAREMBOKMEMORY_API"
    "SAREMBOKAgent_API"  = "SAREMBOKAGENT_API"
    "SAREMBOKVision_API" = "SAREMBOKVISION_API"
    "SAREMBOKVoice_API"  = "SAREMBOKVOICE_API"
}


$Headers = Get-ChildItem `
    $PluginsRoot `
    -Recurse `
    -Filter *.h `
    -ErrorAction SilentlyContinue


foreach($Header in $Headers)
{
    $Content = Get-Content `
        $Header.FullName `
        -Raw

    $Changed = $false

    foreach($Key in $MacroFixes.Keys)
    {
        if($Content.Contains($Key))
        {
            $Content = $Content.Replace(
                $Key,
                $MacroFixes[$Key]
            )

            $Changed = $true
        }
    }


    if($Changed)
    {
        Set-Content `
            -Path $Header.FullName `
            -Value $Content `
            -Encoding UTF8

        Write-Host " Fixed:" $Header.FullName
    }
}



# ------------------------------------------------------------
# Fix SarembokBridge Include Order
# ------------------------------------------------------------

Write-Host ""
Write-Host "[2/5] Fixing SarembokBridge include order..."

$BridgeCPP = Join-Path `
$ProjectRoot `
"Plugins\SarembokBridge\Source\SarembokBridge\Private\SarembokBridge.cpp"


if(Test-Path $BridgeCPP)
{
    $Lines = Get-Content $BridgeCPP

    $Filtered = $Lines | Where-Object {
        $_ -notmatch '#include "SarembokBridge.h"'
    }


    $NewContent = @(
        '#include "SarembokBridge.h"'
    ) + $Filtered


    Set-Content `
        -Path $BridgeCPP `
        -Value $NewContent `
        -Encoding UTF8


    Write-Host " Fixed SarembokBridge.cpp"
}



# ------------------------------------------------------------
# Add WebSockets Dependency
# ------------------------------------------------------------

Write-Host ""
Write-Host "[3/5] Updating SarembokBridge Build.cs..."

$BridgeBuild = Join-Path `
$ProjectRoot `
"Plugins\SarembokBridge\Source\SarembokBridge\SarembokBridge.Build.cs"


if(Test-Path $BridgeBuild)
{
    $BuildText = Get-Content `
        $BridgeBuild `
        -Raw


    if($BuildText -notmatch '"WebSockets"')
    {

        $BuildText = $BuildText.Replace(
            '"Engine"',
            '"Engine",
                "WebSockets"'
        )


        Set-Content `
            -Path $BridgeBuild `
            -Value $BuildText `
            -Encoding UTF8


        Write-Host " Added WebSockets dependency"
    }
    else
    {
        Write-Host " WebSockets already present"
    }
}



# ------------------------------------------------------------
# Clean Unreal Intermediates
# ------------------------------------------------------------

Write-Host ""
Write-Host "[4/5] Cleaning Unreal intermediates..."

Get-ChildItem `
    $PluginsRoot `
    -Directory `
    -Recurse `
    -Filter Intermediate |
ForEach-Object {

    Remove-Item `
        $_.FullName `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue

    Write-Host " Removed:" $_.FullName
}



# ------------------------------------------------------------
# Regenerate + Build
# ------------------------------------------------------------

Write-Host ""
Write-Host "[5/5] Regenerating Unreal project files..."

$UBT = `
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.exe"


& $UBT `
-projectfiles `
-project="$ProjectRoot\SarembokVE.uproject" `
-game `
-progress


Write-Host ""
Write-Host "Starting Unreal build..."

$Build = `
"C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat"


& $Build `
SarembokVEEditor `
Win64 `
Development `
-project="$ProjectRoot\SarembokVE.uproject" `
-progress


Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Repair Complete"
Write-Host "========================================"