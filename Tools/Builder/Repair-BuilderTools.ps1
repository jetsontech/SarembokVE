# ==========================================================
# Sarembok Builder v2.1 Repair
# Creates missing helper tools
# ==========================================================

$BUILDER="C:\Sarembok_VE\Tools\Builder"

Write-Host ""
Write-Host "Repairing Builder tools..."
Write-Host ""


# Verify.ps1

@'
$ROOT="C:\Sarembok_VE"

$files=@(
"Plugins\SarembokBridge\SarembokBridge.uplugin",
"Plugins\SarembokBridge\Source\SarembokBridge\SarembokBridge.Build.cs",
"Plugins\SarembokBridge\Source\SarembokBridge\Public\SarembokRuntimeManager.h",
"Plugins\SarembokBridge\Source\SarembokBridge\Private\SarembokBridge.cpp"
)

Write-Host ""
Write-Host "Sarembok Verification"
Write-Host ""

foreach($file in $files)
{
    $path=Join-Path $ROOT $file

    if(Test-Path $path)
    {
        Write-Host "[OK] $file"
    }
    else
    {
        Write-Host "[FAIL] $file"
    }
}
'@ | Set-Content `
"$BUILDER\Verify.ps1" `
-Encoding UTF8



# Clean.ps1

@'
$ROOT="C:\Sarembok_VE"

$folders=@(
"$ROOT\Intermediate",
"$ROOT\Saved"
)

foreach($folder in $folders)
{
    if(Test-Path $folder)
    {
        Remove-Item `
        $folder `
        -Recurse `
        -Force
    }
}

Write-Host "Sarembok clean complete"
'@ | Set-Content `
"$BUILDER\Clean.ps1" `
-Encoding UTF8



# Build.ps1

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
'@ | Set-Content `
"$BUILDER\Build.ps1" `
-Encoding UTF8



Write-Host ""
Write-Host "========================================"
Write-Host " Builder Tools Repaired"
Write-Host "========================================"