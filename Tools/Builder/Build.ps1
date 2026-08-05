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
