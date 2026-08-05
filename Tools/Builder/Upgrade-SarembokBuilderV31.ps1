# ==========================================================
# Sarembok Builder v3.1
# Unreal Integration Layer
# ==========================================================

$ErrorActionPreference="Stop"


$ROOT="C:\Sarembok_VE"

$BUILDER="$ROOT\Tools\Builder"

$PROJECT_FILE="$ROOT\SarembokVE.uproject"


Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Builder v3.1"
Write-Host " Unreal Integration Layer"
Write-Host "========================================"
Write-Host ""



# ----------------------------------------------------------
# Create Module Registry
# ----------------------------------------------------------

$registry=@'
{
    "Modules":
    [
        {
            "Name":"SarembokBridge",
            "Type":"Core",
            "Dependencies":[]
        },

        {
            "Name":"SarembokAvatar",
            "Type":"DigitalHuman",
            "Dependencies":
            [
                "SarembokBridge"
            ]
        },

        {
            "Name":"SarembokVoice",
            "Type":"AI",
            "Dependencies":
            [
                "SarembokBridge"
            ]
        },

        {
            "Name":"SarembokVision",
            "Type":"AI",
            "Dependencies":
            [
                "SarembokBridge"
            ]
        },

        {
            "Name":"SarembokAgent",
            "Type":"RuntimeAI",
            "Dependencies":
            [
                "SarembokVoice",
                "SarembokVision",
                "SarembokMemory"
            ]
        },

        {
            "Name":"SarembokMemory",
            "Type":"Knowledge",
            "Dependencies":[]
        }
    ]
}
'@


$registry |
Out-File `
"$BUILDER\Modules.json" `
-Encoding UTF8



# ----------------------------------------------------------
# Create DigitalHuman command helper
# ----------------------------------------------------------

$builder="$BUILDER"

$content=Get-Content $builder -Raw



if($content -notmatch "DigitalHuman")
{

$content=$content.Replace(

'"All"
{',

@'
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
'@

)



$content=$content.Replace(

'"All"
',
'"DigitalHuman",
        "All"
'

)


Set-Content `
$builder `
$content `
-Encoding UTF8

}



# ----------------------------------------------------------
# Create Project Registration Tool
# ----------------------------------------------------------

@'
param()

$PROJECT="C:\Sarembok_VE\SarembokVE.uproject"

$data =
Get-Content $PROJECT -Raw |
ConvertFrom-Json


$plugins=@(
"SarembokBridge",
"SarembokAvatar",
"SarembokVoice",
"SarembokVision",
"SarembokAgent",
"SarembokMemory"
)


foreach($p in $plugins)
{

$exists =
$data.Plugins |
Where-Object {
    $_.Name -eq $p
}


if(!$exists)
{
    $obj =
    [PSCustomObject]@{
        Name=$p
        Enabled=$true
    }

    $data.Plugins += $obj

    Write-Host "[+] Registered $p"
}

}


$data |
ConvertTo-Json -Depth 20 |
Set-Content $PROJECT


Write-Host ""
Write-Host "Unreal plugin registration complete"
'@ |
Out-File `
"$BUILDER\Register-UnrealModules.ps1" `
-Encoding UTF8



Write-Host ""
Write-Host "========================================"
Write-Host " Builder v3.1 COMPLETE"
Write-Host "========================================"
