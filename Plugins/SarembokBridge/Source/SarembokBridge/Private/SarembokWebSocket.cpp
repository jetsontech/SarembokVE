#include "SarembokWebSocket.h"
#include "WebSocketsModule.h"

FSarembokWebSocket::FSarembokWebSocket()
{
}

FSarembokWebSocket::~FSarembokWebSocket()
{
    Disconnect();
}

void FSarembokWebSocket::Connect()
{
    if (Socket.IsValid() && Socket->IsConnected())
    {
        return;
    }

    if (!FModuleManager::Get().IsModuleLoaded("WebSockets"))
    {
        FModuleManager::LoadModuleChecked<FWebSocketsModule>("WebSockets");
    }

    const FString ServerURL = TEXT("ws://127.0.0.1:9000/");
    Socket = FWebSocketsModule::Get().CreateWebSocket(ServerURL);

    if (!Socket.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("SarembokBridge failed to create websocket for %s"), *ServerURL);
        return;
    }

    Socket->OnConnected().AddLambda([]()
    {
        UE_LOG(LogTemp, Display, TEXT("SarembokBridge websocket connected."));
    });

    Socket->OnConnectionError().AddLambda([](const FString& Error)
    {
        UE_LOG(LogTemp, Error, TEXT("SarembokBridge websocket connection error: %s"), *Error);
    });

    Socket->OnClosed().AddLambda([](int32 StatusCode, const FString& Reason, bool bWasClean)
    {
        UE_LOG(LogTemp, Display, TEXT("SarembokBridge websocket closed: %d %s clean=%d"), StatusCode, *Reason, bWasClean);
    });

    Socket->Connect();
}

void FSarembokWebSocket::Disconnect()
{
    if (Socket.IsValid())
    {
        Socket->Close();
        Socket.Reset();
    }
}

bool FSarembokWebSocket::IsConnected() const
{
    return Socket.IsValid() && Socket->IsConnected();
}

void FSarembokWebSocket::SendMessage(const FString& Message)
{
    if (!IsConnected())
    {
        UE_LOG(LogTemp, Warning, TEXT("SarembokBridge websocket is disconnected. Attempting reconnect."));
        Connect();
        return;
    }

    UE_LOG(LogTemp, Display, TEXT("SarembokBridge websocket send: %s"), *Message);
    Socket->Send(Message);
}
