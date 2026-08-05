$ROOT="C:\Sarembok_VE\Plugins\SarembokBridge\Source\SarembokBridge"

Write-Host "Fixing Sarembok Bridge source layout"


# Create folders

New-Item "$ROOT\Public" -ItemType Directory -Force | Out-Null
New-Item "$ROOT\Private" -ItemType Directory -Force | Out-Null


# Move headers

if(Test-Path "$ROOT\SarembokBridgeModule.h")
{
Move-Item `
"$ROOT\SarembokBridgeModule.h" `
"$ROOT\Public\SarembokBridgeModule.h" `
-Force
}


if(Test-Path "$ROOT\SarembokRuntimeManager.h")
{
Move-Item `
"$ROOT\SarembokRuntimeManager.h" `
"$ROOT\Public\SarembokRuntimeManager.h" `
-Force
}


# Move cpp files

if(Test-Path "$ROOT\SarembokBridgeModule.cpp")
{
Move-Item `
"$ROOT\SarembokBridgeModule.cpp" `
"$ROOT\Private\SarembokBridgeModule.cpp" `
-Force
}


if(Test-Path "$ROOT\SarembokRuntimeManager.cpp")
{
Move-Item `
"$ROOT\SarembokRuntimeManager.cpp" `
"$ROOT\Private\SarembokRuntimeManager.cpp" `
-Force
}


# Remove generated build junk

Remove-Item `
"C:\Sarembok_VE\Intermediate" `
-Recurse `
-Force `
-ErrorAction SilentlyContinue


Remove-Item `
"C:\Sarembok_VE\Binaries" `
-Recurse `
-Force `
-ErrorAction SilentlyContinue


Write-Host ""
Write-Host "Structure fixed"