# ==========================================================
# Sarembok Builder v3 Router Patch
# Adds Module Factory Commands
# ==========================================================

$ErrorActionPreference="Stop"

$FILE="C:\Sarembok_VE\Tools\Builder\SarembokBuilder.ps1"


Write-Host ""
Write-Host "Patching Sarembok Builder v3 router..."
Write-Host ""


$content = Get-Content $FILE -Raw


# Expand ValidateSet

$content = $content.Replace(
'"Bridge",',
'"Bridge",
        "Avatar",
        "Voice",
        "Vision",
        "Agent",
        "Memory",'
)


# Add switch cases before closing switch

if($content -notmatch '"Avatar"')
{

$content = $content.Replace(

'    "All"
    {
        Create-Bridge
        Create-Runtime
        Create-Plugin
    }',

@'
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


    "All"
    {
        Create-Bridge
        Create-Runtime
        Create-Plugin
        Create-Module "Avatar"
        Create-Module "Voice"
        Create-Module "Vision"
        Create-Module "Agent"
        Create-Module "Memory"
    }
'@

)

}


Set-Content `
$FILE `
$content `
-Encoding UTF8


Write-Host ""
Write-Host "========================================"
Write-Host " Router Patch Complete"
Write-Host "========================================"