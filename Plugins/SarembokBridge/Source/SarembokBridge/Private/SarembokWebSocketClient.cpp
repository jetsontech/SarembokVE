#include "SarembokWebSocketClient.h"

#include "Modules/ModuleManager.h"
#include "WebSocketsModule.h"

FSarembokWebSocketClient::FSarembokWebSocketClient()
{
    ServerURL = TEXT("ws://127.0.0.1:8765");

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
    if (Socket.IsValid() && Socket->IsConnected())
    {
        return;
    }

    if (Socket.IsValid())
    {
        Socket->Close();
        Socket.Reset();
    }

    FWebSocketsModule& Module =
        FModuleManager::LoadModuleChecked<FWebSocketsModule>(TEXT("WebSockets"));

    Socket = Module.CreateWebSocket(ServerURL);

    if (!Socket.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("[SAREMBOK] FAILED to create WebSocket for %s"), *ServerURL);
        return;
    }

    Socket->OnConnected().AddRaw(this, &FSarembokWebSocketClient::OnConnected);
    Socket->OnMessage().AddRaw(this, &FSarembokWebSocketClient::OnMessage);
    Socket->OnConnectionError().AddRaw(this, &FSarembokWebSocketClient::OnConnectionError);
    Socket->OnClosed().AddRaw(this, &FSarembokWebSocketClient::OnClosed);

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] WebSocket connecting to %s"), *ServerURL);
    Socket->Connect();
}

void FSarembokWebSocketClient::Disconnect()
{
    if (!Socket.IsValid())
    {
        return;
    }

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
        UE_LOG(LogTemp, Warning, TEXT("[SAREMBOK] TX FAILED - WebSocket is not connected"));
        return;
    }

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] TX: %s"), *Message);
    Socket->Send(Message);
}

void FSarembokWebSocketClient::OnConnected()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] ========================================"));
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] CONNECTED TO SAREMBOK RUNTIME"));
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Server: %s"), *ServerURL);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] ========================================"));

    SendMessage(TEXT("{\"event\":\"user_detected\"}"));
}

void FSarembokWebSocketClient::OnMessage(const FString& Message)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] RX FROM SAREMBOK RUNTIME: %s"), *Message);
    MessageReceived.Broadcast(Message);
}

void FSarembokWebSocketClient::OnConnectionError(const FString& Error)
{
    UE_LOG(LogTemp, Error, TEXT("[SAREMBOK] WebSocket connection error: %s"), *Error);
}

void FSarembokWebSocketClient::OnClosed(int32 StatusCode, const FString& Reason, bool bWasClean)
{
    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] WebSocket closed: Status=%d Clean=%s Reason=%s"),
        StatusCode,
        bWasClean ? TEXT("true") : TEXT("false"),
        *Reason
    );
}
