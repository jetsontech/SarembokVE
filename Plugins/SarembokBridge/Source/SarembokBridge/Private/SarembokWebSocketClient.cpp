#include "SarembokWebSocketClient.h"
#include "SarembokCommandConstants.h"

#include "Modules/ModuleManager.h"
#include "WebSocketsModule.h"

FSarembokWebSocketClient::FSarembokWebSocketClient()
{
    ServerURL = SarembokCommandConstants::DefaultWebSocketURL;
    Dispatcher = MakeShared<FSarembokMessageDispatcher>();

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] WebSocket Client Created - Server: %s"),
        *ServerURL
    );
}

FSarembokWebSocketClient::~FSarembokWebSocketClient()
{
    Disconnect();
}

void FSarembokWebSocketClient::Connect()
{
    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] Connecting to %s"),
        *ServerURL
    );

    if (Socket.IsValid())
    {
        if (Socket->IsConnected())
        {
            UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] WebSocket is already connected"));
            return;
        }

        Socket->Close();
        Socket.Reset();
    }

    FWebSocketsModule& Module =
        FModuleManager::LoadModuleChecked<FWebSocketsModule>(TEXT("WebSockets"));

    Socket = Module.CreateWebSocket(ServerURL);

    if (!Socket.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("[SAREMBOK] FAILED to create WebSocket"));
        return;
    }

    Socket->OnConnected().AddRaw(this, &FSarembokWebSocketClient::OnConnected);
    Socket->OnMessage().AddRaw(this, &FSarembokWebSocketClient::OnMessage);
    Socket->OnConnectionError().AddRaw(this, &FSarembokWebSocketClient::OnConnectionError);
    Socket->OnClosed().AddRaw(this, &FSarembokWebSocketClient::OnClosed);

    Socket->Connect();
}

void FSarembokWebSocketClient::Disconnect()
{
    if (!Socket.IsValid())
    {
        return;
    }

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Disconnecting from %s"), *ServerURL);

    if (Socket->IsConnected())
    {
        Socket->Close();
    }

    Socket.Reset();
}

void FSarembokWebSocketClient::SendMessage(const FString& Message)
{
    if (!Socket.IsValid() || !Socket->IsConnected())
    {
        UE_LOG(LogTemp, Warning, TEXT("[SAREMBOK] TX FAILED - WebSocket not connected"));
        return;
    }

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] TX: %s"), *Message);
    Socket->Send(Message);
}

void FSarembokWebSocketClient::OnConnected()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] CONNECTED TO SAREMBOK RUNTIME"));
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Server: %s"), *ServerURL);

    const FString TestMessage = TEXT("{\"event\":\"user_detected\"}");
    SendMessage(TestMessage);
}

void FSarembokWebSocketClient::OnMessage(const FString& Message)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] RX FROM SAREMBOK RUNTIME:"));
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] %s"), *Message);

    if (Dispatcher.IsValid())
    {
        Dispatcher->DispatchMessage(Message);
    }
}

void FSarembokWebSocketClient::OnConnectionError(const FString& Error)
{
    UE_LOG(LogTemp, Error, TEXT("[SAREMBOK] WEBSOCKET CONNECTION ERROR: %s"), *Error);
}

void FSarembokWebSocketClient::OnClosed(
    int32 StatusCode,
    const FString& Reason,
    bool bWasClean
)
{
    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] WEBSOCKET CLOSED - Status=%d Clean=%s Reason=%s"),
        StatusCode,
        bWasClean ? TEXT("true") : TEXT("false"),
        *Reason
    );
}
