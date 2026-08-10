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

    Dispatcher = MakeShared<FSarembokMessageDispatcher>();
    WebSocketClient = MakeShared<FSarembokWebSocketClient>();

    WebSocketClient->OnMessageReceived().AddRaw(
        this,
        &FSarembokBridgeService::HandleWebSocketMessage
    );

    WebSocketClient->Connect();
    bReady = true;

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Bridge Service Ready"));
}

void FSarembokBridgeService::Shutdown()
{
    if (WebSocketClient.IsValid())
    {
        WebSocketClient->OnMessageReceived().RemoveAll(this);
        WebSocketClient->Disconnect();
        WebSocketClient.Reset();
    }

    Dispatcher.Reset();
    bReady = false;
}

void FSarembokBridgeService::SendMessage(const FSarembokMessage& Message)
{
    if (WebSocketClient.IsValid())
    {
        WebSocketClient->SendMessage(Message.Data);
    }
}

void FSarembokBridgeService::ReceiveMessage(const FSarembokMessage& Message)
{
    FSarembokMessageRouter::Get().Dispatch(Message);
}

void FSarembokBridgeService::HandleWebSocketMessage(const FString& Message)
{
    if (Dispatcher.IsValid())
    {
        Dispatcher->DispatchMessage(Message);
    }
}
