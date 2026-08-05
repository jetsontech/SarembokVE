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
