#include "SarembokBridgeService.h"

#include "Containers/Ticker.h"

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
    bReady = true;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Bridge Service Ready - network connection deferred")
    );

    // Do not connect during module startup. Defer the network operation until
    // the engine has entered its normal tick loop so an unavailable runtime
    // cannot hold up editor/game initialization.
    FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateLambda(
            [this](float)
            {
                if (!bReady || !WebSocketClient.IsValid())
                {
                    return false;
                }

                UE_LOG(
                    LogTemp,
                    Display,
                    TEXT("Sarembok Bridge Service Starting asynchronous network connection")
                );

                WebSocketClient->Connect();
                return false;
            }
        ),
        0.1f
    );
}

void FSarembokBridgeService::Shutdown()
{
    // Mark the service unavailable before destroying the client. If the
    // deferred ticker callback has not fired yet, it will safely no-op.
    bReady = false;

    if (WebSocketClient.IsValid())
    {
        WebSocketClient->Disconnect();
        WebSocketClient.Reset();
    }
}

void FSarembokBridgeService::SendMessage(const FSarembokMessage& Message)
{
    if (!WebSocketClient.IsValid())
    {
        return;
    }

    WebSocketClient->SendMessage(Message.Data);
}

void FSarembokBridgeService::ReceiveMessage(const FSarembokMessage& Message)
{
    FSarembokMessageRouter::Get().Dispatch(Message);
}
