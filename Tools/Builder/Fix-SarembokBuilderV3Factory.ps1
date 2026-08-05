# ==========================================================
# Sarembok Builder v3 Factory Injection
# ==========================================================

$ErrorActionPreference="Stop"


$FILE="C:\Sarembok_VE\Tools\Builder\SarembokBuilder.ps1"


$content = Get-Content $FILE -Raw


if($content -notmatch "function Create-Module")
{

$function=@'

# ==========================================================
# Sarembok Builder v3 Module Factory
# ==========================================================

function Create-Module($Name)
{

    Write-Host ""
    Write-Host "Creating Sarembok $Name module..."
    Write-Host ""


    $MODULE_ROOT =
    Join-Path $PLUGINS "Sarembok$Name"


    Ensure-Folder `
    "$MODULE_ROOT\Source\Sarembok$Name"


    Ensure-Folder `
    "$MODULE_ROOT\Source\Sarembok$Name\Public"


    Ensure-Folder `
    "$MODULE_ROOT\Source\Sarembok$Name\Private"



    Write-Host "[+] Generating Build.cs"


    Copy-Item `
    "$TEMPLATES\$Name\Sarembok$Name.Build.cs" `
    "$MODULE_ROOT\Source\Sarembok$Name\Sarembok$Name.Build.cs" `
    -Force



    Write-Host "[+] Generating Public headers"


    Copy-Item `
    "$TEMPLATES\$Name\Public\*" `
    "$MODULE_ROOT\Source\Sarembok$Name\Public" `
    -Force



    Write-Host "[+] Generating Private source"


    Copy-Item `
    "$TEMPLATES\$Name\Private\*" `
    "$MODULE_ROOT\Source\Sarembok$Name\Private" `
    -Force



    Write-Host "[+] Generating Plugin"


    Copy-Item `
    "$TEMPLATES\$Name\Sarembok$Name.uplugin" `
    "$MODULE_ROOT\Sarembok$Name.uplugin" `
    -Force



    Write-Host ""
    Write-Host "Sarembok $Name created."
    Write-Host ""

}

'@


$content += $function


Set-Content `
$FILE `
$content `
-Encoding UTF8

}


Write-Host ""
Write-Host "========================================"
Write-Host " Factory Injection Complete"
Write-Host "========================================"