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
