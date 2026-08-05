# Fix-SarembokRuntimeManagerCommit.ps1
# Restores missing UObject implementation and commits runtime migration

$Root = "C:\Sarembok_VE"

$Header = Join-Path $Root "Plugins\SarembokBridge\Source\SarembokBridge\Public\SarembokRuntimeManager.h"
$CPP = Join-Path $Root "Plugins\SarembokBridge\Source\SarembokBridge\Private\SarembokRuntimeManager.cpp"

Write-Host "========================================"
Write-Host " Sarembok Runtime Manager Repair"
Write-Host "========================================"

Set-Location $Root

if (!(Test-Path $Header)) {
    throw "RuntimeManager header missing: $Header"
}

Write-Host "[1/5] Checking RuntimeManager implementation..."

if (!(Test-Path $CPP)) {

    Write-Host "Creating missing RuntimeManager.cpp..."

    @'
#include "SarembokRuntimeManager.h"

void USarembokRuntimeManager::InitializeRuntime()
{
    UE_LOG(LogTemp, Log, TEXT("Sarembok Runtime Manager Initialized"));
}
'@ | Out-File $CPP -Encoding utf8

}
else {
    Write-Host "RuntimeManager.cpp already exists"
}


Write-Host "[2/5] Current header:"
Get-Content $Header


Write-Host "[3/5] Adding files..."

git add .


Write-Host "[4/5] Commit..."

$commitMessage = "Complete Sarembok runtime manager UObject migration"

git commit -m $commitMessage


Write-Host "[5/5] Push..."

git push origin main


Write-Host ""
Write-Host "========================================"
Write-Host " Commit Complete"
Write-Host "========================================"

git log -1 --oneline