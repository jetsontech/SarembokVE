#include "SarembokBridgeService.h"

FSarembokBridgeService::FSarembokBridgeService()
{
}

FSarembokBridgeService& FSarembokBridgeService::Get()
{
    static FSarembokBridgeService Instance;
    return Instance;
}

void FSarembokBridgeService::Initialize()
{
    if (bReady)
    {
        return;
    }

    WebSocketClient = MakeShared<FSarembokWebSocketClient>();
    WebSocketClient->Connect();

    bReady = true;

    UE_LOG(LogTemp, Display, TEXT("Sarembok Bridge Service Ready"));
}

void FSarembokBridgeService::Shutdown()
{
    if (WebSocketClient.IsValid())
    {
        WebSocketClient->Disconnect();
        WebSocketClient.Reset();
    }

    bReady = false;
}

void FSarembokBridgeService::SendMessage(const FSarembokMessage& Message)
{
    if (!WebSocketClient.IsValid())
    {
        return;
    }

    WebSocketClient->SendMessage(Message.Data);
}
