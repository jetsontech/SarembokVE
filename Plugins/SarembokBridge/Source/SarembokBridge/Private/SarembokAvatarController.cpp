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
