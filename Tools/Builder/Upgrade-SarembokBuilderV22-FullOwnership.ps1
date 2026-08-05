# ==========================================================
# Sarembok Builder v2.2
# Full Bridge Ownership Migration
# Existing Plugin -> Builder Templates
# ==========================================================

$ErrorActionPreference = "Stop"


$ROOT = "C:\Sarembok_VE"

$BUILDER = "$ROOT\Tools\Builder"

$PLUGIN_ROOT =
"$ROOT\Plugins\SarembokBridge"

$SOURCE =
"$PLUGIN_ROOT\Source\SarembokBridge"

$TEMPLATE =
"$BUILDER\Templates\Bridge"


Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Builder v2.2"
Write-Host " Full Ownership Migration"
Write-Host "========================================"
Write-Host ""


# ----------------------------------------------------------
# Create Template Structure
# ----------------------------------------------------------

Write-Host "[1/5] Creating template structure"


New-Item `
-Type Directory `
-Force `
-Path "$TEMPLATE\Public" | Out-Null


New-Item `
-Type Directory `
-Force `
-Path "$TEMPLATE\Private" | Out-Null



# ----------------------------------------------------------
# Copy Existing Plugin Into Templates
# ----------------------------------------------------------

Write-Host "[2/5] Capturing existing Bridge"


Copy-Item `
"$SOURCE\Public\*" `
"$TEMPLATE\Public" `
-Force


Copy-Item `
"$SOURCE\Private\*" `
"$TEMPLATE\Private" `
-Force


Copy-Item `
"$SOURCE\SarembokBridge.Build.cs" `
"$TEMPLATE\SarembokBridge.Build.cs" `
-Force


Copy-Item `
"$PLUGIN_ROOT\SarembokBridge.uplugin" `
"$TEMPLATE\SarembokBridge.uplugin" `
-Force



# ----------------------------------------------------------
# Update Builder
# ----------------------------------------------------------

Write-Host "[3/5] Updating SarembokBuilder"


$BUILDER_FILE =
"$BUILDER\SarembokBuilder.ps1"


$content =
Get-Content $BUILDER_FILE -Raw



if($content -notmatch "Full Ownership")
{

$content = $content.Replace(

'Write-Host "SarembokBridge generated successfully."',

@'

    # Full Ownership Copy

    Write-Host ""
    Write-Host "[+] Copying Public headers"

    Copy-Item `
    "$TEMPLATES\Bridge\Public\*" `
    "$PLUGIN_ROOT\Source\SarembokBridge\Public" `
    -Force


    Write-Host "[+] Copying Private sources"

    Copy-Item `
    "$TEMPLATES\Bridge\Private\*" `
    "$PLUGIN_ROOT\Source\SarembokBridge\Private" `
    -Force


    Write-Host "[+] Full Ownership Migration Active"


    Write-Host ""
    Write-Host "SarembokBridge generated successfully."
'@

)


Set-Content `
$BUILDER_FILE `
$content

}



# ----------------------------------------------------------
# Add Ownership Verification
# ----------------------------------------------------------

Write-Host "[4/5] Creating ownership verifier"


@'
$ROOT="C:\Sarembok_VE"

$FILES=@(

"Plugins\SarembokBridge\Source\SarembokBridge\Public\SarembokAvatarController.h",
"Plugins\SarembokBridge\Source\SarembokBridge\Public\SarembokBridge.h",
"Plugins\SarembokBridge\Source\SarembokBridge\Public\SarembokMessage.h",
"Plugins\SarembokBridge\Source\SarembokBridge\Public\SarembokWebSocket.h",

"Plugins\SarembokBridge\Source\SarembokBridge\Private\SarembokAvatarController.cpp",
"Plugins\SarembokBridge\Source\SarembokBridge\Private\SarembokBridgeModule.cpp",
"Plugins\SarembokBridge\Source\SarembokBridge\Private\SarembokWebSocket.cpp",
"Plugins\SarembokBridge\Source\SarembokBridge\Private\SarembokWebSocketClient.cpp"

)


Write-Host ""
Write-Host "Sarembok Bridge Ownership Check"
Write-Host ""


foreach($file in $FILES)
{

$path=Join-Path $ROOT $file


if(Test-Path $path)
{
Write-Host "[OK] $file"
}
else
{
Write-Host "[MISSING] $file"
}

}
'@ |
Set-Content `
"$BUILDER\Verify-BridgeOwnership.ps1" `
-Encoding UTF8



# ----------------------------------------------------------
# Regenerate
# ----------------------------------------------------------

Write-Host "[5/5] Regenerating Bridge"


Set-Location $BUILDER


.\SarembokBuilder.ps1 -Create Bridge



Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Builder v2.2 COMPLETE"
Write-Host "========================================"