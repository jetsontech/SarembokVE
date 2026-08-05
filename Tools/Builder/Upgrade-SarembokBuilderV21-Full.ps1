# ==========================================================
# Sarembok Builder v2.1 Full Migration
# Existing Plugin -> Template Driven Builder
# ==========================================================

$ErrorActionPreference="Stop"

$ROOT="C:\Sarembok_VE"
$BUILDER="$ROOT\Tools\Builder"

$PLUGIN="$ROOT\Plugins\SarembokBridge\Source\SarembokBridge"

$TEMPLATE="$BUILDER\Templates\Bridge"

Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Builder v2.1 Migration"
Write-Host "========================================"
Write-Host ""


# ----------------------------------------------------------
# Create template structure
# ----------------------------------------------------------

$folders=@(
"$TEMPLATE",
"$TEMPLATE\Public",
"$TEMPLATE\Private"
)

foreach($f in $folders)
{
    New-Item `
    -ItemType Directory `
    -Force `
    -Path $f | Out-Null
}


# ----------------------------------------------------------
# Copy existing working Bridge into templates
# ----------------------------------------------------------

Write-Host "Migrating existing SarembokBridge sources..."

Copy-Item `
"$PLUGIN\Public\*" `
"$TEMPLATE\Public" `
-Force


Copy-Item `
"$PLUGIN\Private\*" `
"$TEMPLATE\Private" `
-Force


Copy-Item `
"$ROOT\Plugins\SarembokBridge\SarembokBridge.uplugin" `
"$TEMPLATE\SarembokBridge.uplugin" `
-Force


Copy-Item `
"$PLUGIN\SarembokBridge.Build.cs" `
"$TEMPLATE\SarembokBridge.Build.cs" `
-Force


Write-Host "[OK] Existing Bridge migrated"



# ----------------------------------------------------------
# Update Builder generation
# ----------------------------------------------------------

$BUILDERFILE="$BUILDER\SarembokBuilder.ps1"

$builder=Get-Content $BUILDERFILE -Raw


if($builder -notmatch "Templates\\Bridge\\Public")
{

$builder=$builder.Replace(

'Ensure-Folder `
        (Join-Path $PLUGIN_ROOT "Source\SarembokBridge\Private")',

@'
Ensure-Folder `
        (Join-Path $PLUGIN_ROOT "Source\SarembokBridge\Private")


    Ensure-Folder `
        (Join-Path $PLUGIN_ROOT "Source\SarembokBridge\Public")
'@
)


$insert=@'

    Copy-Item `
        "$TEMPLATES\Bridge\Public\*" `
        "$PLUGIN_ROOT\Source\SarembokBridge\Public" `
        -Force


    Copy-Item `
        "$TEMPLATES\Bridge\Private\*" `
        "$PLUGIN_ROOT\Source\SarembokBridge\Private" `
        -Force

'@


$builder=$builder.Replace(
'Write-Template `
        "$TEMPLATES\Bridge\SarembokRuntimeManager.cpp"',
$insert+
'    Write-Template `
        "$TEMPLATES\Bridge\SarembokRuntimeManager.cpp"'
)


Set-Content `
$BUILDERFILE `
$builder

}


Write-Host "[OK] Builder upgraded"



# ----------------------------------------------------------
# Create Verify.ps1
# ----------------------------------------------------------

@'
$files=@(
"Plugins\SarembokBridge\SarembokBridge.uplugin",
"Plugins\SarembokBridge\Source\SarembokBridge\SarembokBridge.Build.cs",
"Plugins\SarembokBridge\Source\SarembokBridge\Public\SarembokRuntimeManager.h",
"Plugins\SarembokBridge\Source\SarembokBridge\Private\SarembokBridge.cpp"
)

Write-Host ""
Write-Host "Sarembok Verification"
Write-Host ""

foreach($f in $files)
{
    if(Test-Path "C:\Sarembok_VE\$f")
    {
        Write-Host "[OK] $f"
    }
    else
    {
        Write-Host "[FAIL] $f"
    }
}
'@ | Out-File `
"$BUILDER\Verify.ps1" `
-Encoding utf8



# ----------------------------------------------------------
# Create Clean.ps1
# ----------------------------------------------------------

@'
$ROOT="C:\Sarembok_VE"

Remove-Item "$ROOT\Intermediate" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$ROOT\Saved" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Sarembok clean complete"
'@ | Out-File `
"$BUILDER\Clean.ps1" `
-Encoding utf8



# ----------------------------------------------------------
# Create Build.ps1
# ----------------------------------------------------------

@'
$ROOT="C:\Sarembok_VE"

$UE=Get-ChildItem `
"C:\Program Files\Epic Games" `
-Recurse `
-Filter Build.bat `
-ErrorAction SilentlyContinue |
Where-Object {
    $_.FullName -match "UE_5"
} |
Select-Object -First 1


if($null -eq $UE)
{
    throw "Unreal Engine Build.bat not found"
}


& $UE.FullName `
SarembokVEEditor `
Win64 `
Development `
"$ROOT\SarembokVE.uproject"
'@ | Out-File `
"$BUILDER\Build.ps1" `
-Encoding utf8



# ----------------------------------------------------------
# Generate
# ----------------------------------------------------------

Set-Location $BUILDER


Write-Host ""
Write-Host "Regenerating SarembokBridge..."
Write-Host ""


.\SarembokBuilder.ps1 -Create Bridge



Write-Host ""
Write-Host "========================================"
Write-Host " Sarembok Builder v2.1 COMPLETE"
Write-Host "========================================"