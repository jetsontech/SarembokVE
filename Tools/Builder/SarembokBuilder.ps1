# ==========================================================
# Sarembok Builder v3
# Digital Human Module Factory
# ==========================================================

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet(
        "Bridge",
        "Avatar",
        "Voice",
        "Vision",
        "Agent",
        "Memory",
        "DigitalHuman",
        "All"
    )]
    [string]$Create
)


$ErrorActionPreference="Stop"


$BUILDER = $PSScriptRoot

$PROJECT = Split-Path `
-Parent `
(Split-Path `
-Parent `
$BUILDER)


$TEMPLATES =
Join-Path `
$BUILDER `
"Templates"


$PLUGINS =
Join-Path `
$PROJECT `
"Plugins"



function Ensure-Folder($Path)
{
    if(!(Test-Path $Path))
    {
        New-Item `
        -ItemType Directory `
        -Force `
        -Path $Path | Out-Null
    }
}



function Create-Bridge
{

    Write-Host ""
    Write-Host "Creating SarembokBridge..."
    

    $NAME="SarembokBridge"

    $ROOT=
    Join-Path `
    $PLUGINS `
    $NAME


    Ensure-Folder `
    "$ROOT\Source\$NAME\Public"


    Ensure-Folder `
    "$ROOT\Source\$NAME\Private"


    Copy-Item `
    "$TEMPLATES\Bridge\SarembokBridge.Build.cs" `
    "$ROOT\Source\$NAME\SarembokBridge.Build.cs" `
    -Force


    Copy-Item `
    "$TEMPLATES\Bridge\Public\*" `
    "$ROOT\Source\$NAME\Public" `
    -Force


    Copy-Item `
    "$TEMPLATES\Bridge\Private\*" `
    "$ROOT\Source\$NAME\Private" `
    -Force


    Copy-Item `
    "$TEMPLATES\Bridge\SarembokBridge.uplugin" `
    "$ROOT\SarembokBridge.uplugin" `
    -Force


    Write-Host "SarembokBridge generated."

}



function Create-Module($Name)
{

    Write-Host ""
    Write-Host "Creating Sarembok$Name..."


    $ROOT =
    Join-Path `
    $PLUGINS `
    "Sarembok$Name"


    Ensure-Folder `
    "$ROOT\Source\Sarembok$Name\Public"


    Ensure-Folder `
    "$ROOT\Source\Sarembok$Name\Private"


    Copy-Item `
    "$TEMPLATES\$Name\Sarembok$Name.Build.cs" `
    "$ROOT\Source\Sarembok$Name\Sarembok$Name.Build.cs" `
    -Force


    Copy-Item `
    "$TEMPLATES\$Name\Public\*" `
    "$ROOT\Source\Sarembok$Name\Public" `
    -Force


    Copy-Item `
    "$TEMPLATES\$Name\Private\*" `
    "$ROOT\Source\Sarembok$Name\Private" `
    -Force


    Copy-Item `
    "$TEMPLATES\$Name\Sarembok$Name.uplugin" `
    "$ROOT\Sarembok$Name.uplugin" `
    -Force


    Write-Host "Sarembok$Name created."

}



Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Builder v3"
Write-Host "========================================"


switch($Create)
{

"Bridge"
{
    Create-Bridge
}


"Avatar"
{
    Create-Module "Avatar"
}


"Voice"
{
    Create-Module "Voice"
}


"Vision"
{
    Create-Module "Vision"
}


"Agent"
{
    Create-Module "Agent"
}


"Memory"
{
    Create-Module "Memory"
}


"DigitalHuman"
{
    Create-Bridge

    Create-Module "Avatar"
    Create-Module "Voice"
    Create-Module "Vision"
    Create-Module "Agent"
    Create-Module "Memory"
}


"All"
{
    Create-Bridge

    Create-Module "Avatar"
    Create-Module "Voice"
    Create-Module "Vision"
    Create-Module "Agent"
    Create-Module "Memory"
}

}


Write-Host ""
Write-Host "========================================"
Write-Host " BUILD COMPLETE"
Write-Host "========================================"
