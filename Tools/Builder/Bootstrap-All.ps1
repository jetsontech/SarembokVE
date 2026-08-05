# ==========================================================
# Sarembok VE Full Runtime Bootstrap v0.4
# Unreal Engine 5.8 + Runtime Connector
# ==========================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=========================================="
Write-Host " Sarembok VE Full Runtime Bootstrap v0.4"
Write-Host "=========================================="
Write-Host ""

$ROOT = "C:\Sarembok_VE"


# ==========================================================
# Create Runtime Structure
# ==========================================================

$Folders = @(
    "AI\Runtime\connection",
    "AI\Runtime\events",
    "AI\Runtime\state",
    "Backend\WebSocket",
    "Logs",
    "Content\Avatar"
)

foreach ($Folder in $Folders)
{
    $Path = Join-Path $ROOT $Folder

    if (!(Test-Path $Path))
    {
        New-Item `
            -ItemType Directory `
            -Path $Path `
            | Out-Null

        Write-Host "[DIR] $Path"
    }
}


# ==========================================================
# Runtime Configuration
# ==========================================================

$RuntimeConfig = @"
{
    "name": "SarembokVE",
    "version": "0.4",
    "endpoint": "ws://127.0.0.1:9000",
    "mode": "digital_human"
}
"@

$RuntimeConfig |
Out-File `
"$ROOT\AI\Runtime\connection\runtime.json" `
-Encoding utf8


Write-Host "[CONFIG] Runtime configuration created"


# ==========================================================
# WebSocket Runtime Server
# ==========================================================

$Server = @'
import asyncio
import json
import websockets


async def client(websocket):

    print("Sarembok Client Connected")

    try:

        async for message in websocket:

            print("Received:")
            print(message)

            response = {
                "type": "ai_response",
                "text": "Sarembok Runtime Online",
                "state": "active"
            }

            await websocket.send(
                json.dumps(response)
            )

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")



async def main():

    print("")
    print("==============================")
    print(" Sarembok WebSocket Runtime")
    print(" Port: 9000")
    print("==============================")
    print("")


    async with websockets.serve(
        client,
        "0.0.0.0",
        9000
    ):

        await asyncio.Future()



asyncio.run(main())
'@


$Server |
Out-File `
"$ROOT\Backend\WebSocket\server.py" `
-Encoding utf8


"websockets" |
Out-File `
"$ROOT\Backend\WebSocket\requirements.txt" `
-Encoding utf8


Write-Host "[BACKEND] WebSocket runtime created"


# ==========================================================
# Locate Visual Studio MSBuild
# ==========================================================

$MSBuildCandidates = @(

"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe",

"C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe",

"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe"

)


$MSBuild = $null


foreach ($Candidate in $MSBuildCandidates)
{
    if(Test-Path $Candidate)
    {
        $MSBuild = $Candidate
        break
    }
}


if($null -eq $MSBuild)
{
    throw "Visual Studio 2022 MSBuild not found"
}


Write-Host ""
Write-Host "[BUILD] Unreal Project"
Write-Host $MSBuild
Write-Host ""


# ==========================================================
# Build Unreal
# ==========================================================

& $MSBuild `
"$ROOT\SarembokVE.sln" `
/t:Build `
/p:Configuration="Development Editor" `
/p:Platform=Win64


if($LASTEXITCODE -ne 0)
{
    throw "Unreal build failed"
}


# ==========================================================
# Complete
# ==========================================================

Write-Host ""
Write-Host "=========================================="
Write-Host " Sarembok VE Bootstrap Complete"
Write-Host "=========================================="
Write-Host ""

Write-Host "Runtime:"
Write-Host " ws://127.0.0.1:9000"

Write-Host ""
Write-Host "Next:"
Write-Host " python Backend\WebSocket\server.py"
Write-Host ""