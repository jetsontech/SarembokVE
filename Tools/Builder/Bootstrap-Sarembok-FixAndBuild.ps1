# ==========================================================
# SarembokBuilder v2
# Single Source Unreal Code Generator
# ==========================================================

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet(
        "Bridge",
        "Runtime",
        "Plugin",
        "All"
    )]
    [string]$Create
)

$ErrorActionPreference = "Stop"

$PROJECT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$TEMPLATES = Join-Path $PSScriptRoot "Templates"
$PLUGINS = Join-Path $PROJECT "Plugins"


function Write-Header {
    Write-Host ""
    Write-Host "========================================"
    Write-Host " Sarembok Builder v2"
    Write-Host "========================================"
    Write-Host ""
}


function New-Folder($path)
{
    if (!(Test-Path $path))
    {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Host "[+] Created $path"
    }
}


function Write-Template($template,$destination)
{
    if (!(Test-Path $template))
    {
        throw "Missing template: $template"
    }

    Copy-Item `
        -Path $template `
        -Destination $destination `
        -Force

    Write-Host "[+] Generated $destination"
}


function New-Bridge
{

    Write-Host ""
    Write-Host "Creating SarembokBridge..."

    $PLUGIN_ROOT =
        Join-Path $PLUGINS "SarembokBridge"


    New-Folder $PLUGIN_ROOT

    New-Folder `
        (Join-Path $PLUGIN_ROOT "Source")

    New-Folder `
        (Join-Path $PLUGIN_ROOT "Source\SarembokBridge")

    New-Folder `
        (Join-Path $PLUGIN_ROOT "Source\SarembokBridge\Public")

    New-Folder `
        (Join-Path $PLUGIN_ROOT "Source\SarembokBridge\Private")


    Write-Template `
        "$TEMPLATES\Bridge\SarembokBridge.Build.cs" `
        "$PLUGIN_ROOT\Source\SarembokBridge\SarembokBridge.Build.cs"


    Write-Template `
        "$TEMPLATES\Bridge\SarembokRuntimeManager.h" `
        "$PLUGIN_ROOT\Source\SarembokBridge\Public\SarembokRuntimeManager.h"


    Write-Template `
        "$TEMPLATES\Bridge\SarembokRuntimeManager.cpp" `
        "$PLUGIN_ROOT\Source\SarembokBridge\Private\SarembokRuntimeManager.cpp"


    Write-Template `
        "$TEMPLATES\Bridge\SarembokBridge.uplugin" `
        "$PLUGIN_ROOT\SarembokBridge.uplugin"


    Write-Host ""
    Write-Host "SarembokBridge generated successfully."
}



function New-Runtime
{
    Write-Host "Runtime generation placeholder"
}



function New-Plugin
{
    Write-Host "Plugin generation placeholder"
}



Write-Header


switch($Create)
{

    "Bridge"
    {
        New-Bridge
    }


    "Runtime"
    {
        New-Runtime
    }


    "Plugin"
    {
        New-Plugin
    }


    "All"
    {
        New-Bridge
        New-Runtime
        New-Plugin
    }

}


Write-Host ""
Write-Host "BUILD COMPLETE"
Write-Host ""