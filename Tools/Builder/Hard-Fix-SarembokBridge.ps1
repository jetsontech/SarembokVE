Write-Host "====================================="
Write-Host " Sarembok Bridge Hard Repair"
Write-Host "====================================="

$Root="C:\Sarembok_VE\Plugins\SarembokBridge\Source\SarembokBridge"

Write-Host "[SCAN] Current files"

Get-ChildItem $Root -Recurse -File | 
Select FullName


Write-Host ""
Write-Host "[REMOVE] Root duplicates"

$Remove=@(
"SarembokBridgeModule.cpp",
"SarembokBridgeModule.h",
"SarembokRuntimeManager.cpp",
"SarembokRuntimeManager.h"
)

foreach($f in $Remove){

    $path="$Root\$f"

    if(Test-Path $path){

        Write-Host "Deleting $path"
        Remove-Item $path -Force

    }
}


Write-Host ""
Write-Host "[VERIFY] Moving correct files"


# Restore folders
New-Item "$Root\Public" -ItemType Directory -Force | Out-Null
New-Item "$Root\Private" -ItemType Directory -Force | Out-Null


# Delete Unreal generated files

Write-Host ""
Write-Host "[CLEAN] Unreal cache"

$clean=@(
"C:\Sarembok_VE\Intermediate",
"C:\Sarembok_VE\Binaries",
"C:\Sarembok_VE\Saved"
)

foreach($c in $clean){

 if(Test-Path $c){

    Remove-Item $c -Recurse -Force
    Write-Host "Removed $c"

 }

}


Write-Host ""
Write-Host "Bridge repair complete"