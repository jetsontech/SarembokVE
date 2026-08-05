# ==========================================================
# Fix Sarembok Builder v3 Switch
# ==========================================================

$FILE="C:\Sarembok_VE\Tools\Builder\SarembokBuilder.ps1"

$content=Get-Content $FILE -Raw


if($content -notmatch 'Create-Module "Avatar"')
{

$old=@'
    "All"
    {
        Create-Bridge
        Create-Runtime
        Create-Plugin
    }
'@


$new=@'
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


$content=$content.Replace($old,$new)


Set-Content `
$FILE `
$content `
-Encoding UTF8

}


Write-Host ""
Write-Host "Builder v3 switch repaired"