# ============================================================
# Fix-SarembokRuntimeDependency.ps1
# Removes invalid SarembokRuntime module dependency
# ============================================================

$Root = "C:\Sarembok_VE"

$BuildCS = Join-Path `
$Root `
"Plugins\SarembokBridge\Source\SarembokBridge\SarembokBridge.Build.cs"


Write-Host ""
Write-Host "========================================"
Write-Host " Fix SarembokRuntime Dependency"
Write-Host "========================================"


if(Test-Path $BuildCS)
{

    $Content = Get-Content `
    $BuildCS `
    -Raw


    $Content = $Content.Replace(
        '"SarembokRuntime",',
        ''
    )


    $Content = $Content.Replace(
        '"SarembokRuntime"',
        ''
    )


    Set-Content `
    -Path $BuildCS `
    -Value $Content `
    -Encoding UTF8


    Write-Host "Removed invalid SarembokRuntime dependency"

}



Write-Host ""
Write-Host "Cleaning Unreal cache..."


Get-ChildItem `
"$Root\Plugins" `
-Recurse `
-Directory `
-Filter Intermediate |
Remove-Item `
-Recurse `
-Force `
-ErrorAction SilentlyContinue



Write-Host ""
Write-Host "Regenerating project files..."


& "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.exe" `
-projectfiles `
-project="$Root\SarembokVE.uproject" `
-game `
-progress



Write-Host ""
Write-Host "Building..."


& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" `
SarembokVEEditor `
Win64 `
Development `
-project="$Root\SarembokVE.uproject" `
-progress


Write-Host ""
Write-Host "========================================"
Write-Host " COMPLETE"
Write-Host "========================================"