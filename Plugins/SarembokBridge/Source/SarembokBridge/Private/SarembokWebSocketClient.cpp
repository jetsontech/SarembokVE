#include "SarembokWebSocketClient.h"
#include "SarembokCommandConstants.h"

#include "Modules/ModuleManager.h"
#include "WebSocketsModule.h"

FSarembokWebSocketClient::FSarembokWebSocketClient()
{
    ServerURL = SarembokCommandConstants::DefaultWebSocketURL;
    AuthToken = TEXT("");
    bAutoReconnect = true;
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

void FSarembokWebSocketClient::SetServerURL(const FString& InURL)
{
    if (!InURL.IsEmpty())
    {
        ServerURL = InURL;
    }
}

void FSarembokWebSocketClient::SetAuthToken(const FString& InAuthToken)
{
    AuthToken = InAuthToken;
}

void FSarembokWebSocketClient::Connect()
{
    Connect(ServerURL, AuthToken);
}

void FSarembokWebSocketClient::Connect(const FString& InURL, const FString& InAuthToken)
{
    SetServerURL(InURL);
    SetAuthToken(InAuthToken);

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] Connecting to %s (Auth: %s)"),
        *ServerURL,
        AuthToken.IsEmpty() ? TEXT("None") : TEXT("Configured")
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
        UE_LOG(LogTemp, Error, TEXT("[SAREMBOK] FAILED to create WebSocket for %s"), *ServerURL);
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
    bAutoReconnect = false;
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

void FSarembokWebSocketClient::SendRPC(const FString& Method, const FString& ParamsJson, int32 RequestId)
{
    FString AuthParam = TEXT("");
    if (!AuthToken.IsEmpty())
    {
        AuthParam = FString::Printf(TEXT(",\"authToken\":\"%s\""), *AuthToken);
    }

    FString BodyParams = ParamsJson.TrimStartAndEnd();
    if (BodyParams.StartsWith(TEXT("{")) && BodyParams.EndsWith(TEXT("}")))
    {
        FString Inner = BodyParams.Mid(1, BodyParams.Len() - 2).TrimStartAndEnd();
        if (Inner.IsEmpty())
        {
            BodyParams = FString::Printf(TEXT("{%s}"), AuthParam.StartsWith(TEXT(",")) ? *AuthParam.Mid(1) : *AuthParam);
        }
        else
        {
            BodyParams = FString::Printf(TEXT("{%s%s}"), *Inner, *AuthParam);
        }
    }
    else
    {
        BodyParams = FString::Printf(TEXT("{%s}"), AuthParam.StartsWith(TEXT(",")) ? *AuthParam.Mid(1) : *AuthParam);
    }

    const FString Payload = FString::Printf(
        TEXT("{\"jsonrpc\":\"2.0\",\"id\":%d,\"method\":\"%s\",\"params\":%s}"),
        RequestId,
        *Method,
        *BodyParams
    );

    SendMessage(Payload);
}

void FSarembokWebSocketClient::OnConnected()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] CONNECTED TO SAREMBOK RUNTIME"));
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Server: %s"), *ServerURL);

    // Initial RPC Health ping with authentication
    SendRPC(TEXT("Health"), TEXT("{}"), 100);
}

void FSarembokWebSocketClient::OnMessage(const FString& Message)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] RX FROM SAREMBOK RUNTIME: %s"), *Message);

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
