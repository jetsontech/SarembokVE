# ==================================================
# SarembokBridge v0.3 Bootstrap
# WebSocket + Avatar Control Layer
# ==================================================

$Root="C:\Sarembok_VE"

$Plugin="$Root\Plugins\SarembokBridge"

Write-Host ""
Write-Host "===================================="
Write-Host " SarembokBridge v0.3 Bootstrap"
Write-Host "===================================="


$Public="$Plugin\Source\SarembokBridge\Public"
$Private="$Plugin\Source\SarembokBridge\Private"


# -----------------------------
# Create headers
# -----------------------------

$Files=@{


"Public\SarembokMessage.h"=@'
#pragma once

#include "CoreMinimal.h"

USTRUCT(BlueprintType)
struct FSarembokMessage
{

GENERATED_BODY()


UPROPERTY(BlueprintReadWrite)
FString Event;


UPROPERTY(BlueprintReadWrite)
FString Data;


};
'@



"Public\SarembokWebSocket.h"=@'
#pragma once

#include "CoreMinimal.h"
#include "IWebSocket.h"


class FSarembokWebSocket
{

public:


void Connect();


void Send(
FString Event,
FString Data
);


private:

TSharedPtr<IWebSocket> Socket;


};
'@



"Public\SarembokAvatarController.h"=@'
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokAvatarController.generated.h"


UCLASS()
class SAREMBOKBRIDGE_API ASarembokAvatarController
:
public AActor
{

GENERATED_BODY()


public:

ASarembokAvatarController();


UFUNCTION(BlueprintCallable)
void SendChat(
FString Message
);


};
'@



# -----------------------------
# CPP
# -----------------------------


"Private\SarembokWebSocket.cpp"=@'
#include "SarembokWebSocket.h"

#include "WebSocketsModule.h"


void FSarembokWebSocket::Connect()
{

FWebSocketsModule::Get().StartupModule();


Socket =
FWebSocketsModule::Get()
.CreateWebSocket(
"ws://127.0.0.1:9000"
);


Socket->Connect();


}



void FSarembokWebSocket::Send(
FString Event,
FString Data
)
{

if(Socket.IsValid())
{

Socket->Send(
"{\"event\":\""+Event+
"\",\"data\":\""+Data+"\"}"
);

}

}
'@



"Private\SarembokAvatarController.cpp"=@'
#include "SarembokAvatarController.h"
#include "SarembokWebSocket.h"


ASarembokAvatarController::
ASarembokAvatarController()
{

PrimaryActorTick.bCanEverTick=false;

}


void ASarembokAvatarController::
SendChat(FString Message)
{

FSarembokWebSocket Bridge;

Bridge.Connect();

Bridge.Send(
"CHAT",
Message
);

}
'@


}



foreach($file in $Files.Keys)
{

$target=""

if($file.StartsWith("Public"))
{
$target=Join-Path $Public ($file.Replace("Public\",""))
}
else
{
$target=Join-Path $Private ($file.Replace("Private\",""))
}


if(!(Test-Path $target))
{

Set-Content `
-Path $target `
-Value $Files[$file]


Write-Host "[CREATED] $target"

}

}



# Protocol update

$Protocol=@'
{
"version":"0.3",
"connection":
{
"type":"websocket",
"url":"ws://127.0.0.1:9000"
},

"events":
[
"CHAT",
"VOICE",
"VISION",
"EMOTION",
"FACIAL",
"GESTURE"
]

}
'@


Set-Content `
"$Root\Backend\WebSocket\protocol.json" `
$Protocol


Write-Host ""
Write-Host "===================================="
Write-Host " SarembokBridge v0.3 Complete"
Write-Host "===================================="