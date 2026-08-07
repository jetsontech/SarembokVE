#pragma once

#include "CoreMinimal.h"
#include "SarembokWebSocketClient.h"
#include "SarembokMessageDispatcher.h"

class FSarembokBridgeRuntime
{
public:

    FSarembokBridgeRuntime();
    ~FSarembokBridgeRuntime();

    void Initialize();
    void Shutdown();

    void SendCommand(const FString& Command,
                     const FString& Target,
                     const FString& Payload);

private:

    TSharedPtr<FSarembokWebSocketClient> Client;
    TSharedPtr<FSarembokMessageDispatcher> Dispatcher;
};
