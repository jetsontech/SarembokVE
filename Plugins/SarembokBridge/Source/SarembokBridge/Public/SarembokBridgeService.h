#pragma once

#include "CoreMinimal.h"
#include "SarembokMessage.h"
#include "SarembokWebSocketClient.h"
#include "SarembokMessageRouter.h"

class SAREMBOKBRIDGE_API FSarembokBridgeService
{
public:

    static FSarembokBridgeService& Get();

    void Initialize();
    void Shutdown();

    void SendMessage(const FSarembokMessage& Message);
    void ReceiveMessage(const FSarembokMessage& Message);

    bool IsReady() const { return bReady; }

private:

    FSarembokBridgeService();

    TSharedPtr<FSarembokWebSocketClient> WebSocketClient;

    bool bReady = false;
};
