#include "SarembokWebSocketClient.h"

#include "WebSocketsModule.h"

FSarembokWebSocketClient::FSarembokWebSocketClient()
{
    ServerURL = TEXT("ws://127.0.0.1:8765");
}

FSarembokWebSocketClient::~FSarembokWebSocketClient()
{
    Disconnect();
}

void FSarembokWebSocketClient::Connect()
{
    FWebSocketsModule& Module = FModuleManager::LoadModuleChecked<FWebSocketsModule>("WebSockets");

    Socket = Module.CreateWebSocket(ServerURL);

    Socket->OnConnected().AddRaw(this, &FSarembokWebSocketClient::OnConnected);
    Socket->OnMessage().AddRaw(this, &FSarembokWebSocketClient::OnMessage);
    Socket->OnConnectionError().AddRaw(this, &FSarembokWebSocketClient::OnConnectionError);
    Socket->OnClosed().AddRaw(this, &FSarembokWebSocketClient::OnClosed);

    Socket->Connect();
}

void FSarembokWebSocketClient::Disconnect()
{
    if (Socket.IsValid())
    {
        Socket->Close();
        Socket.Reset();
    }

    bConnected = false;
}

void FSarembokWebSocketClient::SendMessage(const FString& Message)
{
    if (Socket.IsValid() && Socket->IsConnected())
    {
        Socket->Send(Message);
    }
}

void FSarembokWebSocketClient::OnConnected()
{
    bConnected = true;
    UE_LOG(LogTemp, Display, TEXT("Connected to Sarembok Core"));
}

void FSarembokWebSocketClient::OnMessage(const FString& Message)
{
    UE_LOG(LogTemp, Display, TEXT("Sarembok Message: %s"), *Message);
}

void FSarembokWebSocketClient::OnConnectionError(const FString& Error)
{
    bConnected = false;
    UE_LOG(LogTemp, Error, TEXT("Sarembok Connection Error: %s"), *Error);
}

void FSarembokWebSocketClient::OnClosed(int32 StatusCode, const FString& Reason, bool bWasClean)
{
    bConnected = false;
    UE_LOG(LogTemp, Display, TEXT("Sarembok Connection Closed"));
}
