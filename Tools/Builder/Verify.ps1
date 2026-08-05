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
