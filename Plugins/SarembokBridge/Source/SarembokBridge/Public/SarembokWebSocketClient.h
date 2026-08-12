#pragma once

#include "CoreMinimal.h"
#include "IWebSocket.h"
#include "SarembokMessageDispatcher.h"

class FSarembokWebSocketClient
{
public:

    FSarembokWebSocketClient();

    ~FSarembokWebSocketClient();

    void Connect();
    void Connect(const FString& InURL, const FString& InAuthToken = TEXT(""));

    void Disconnect();

    void SetServerURL(const FString& InURL);
    void SetAuthToken(const FString& InAuthToken);

    void SendMessage(const FString& Message);
    void SendRPC(const FString& Method, const FString& ParamsJson = TEXT("{}"), int32 RequestId = 1);

private:

    void OnConnected();

    void OnMessage(const FString& Message);

    void OnConnectionError(const FString& Error);

    void OnClosed(
        int32 StatusCode,
        const FString& Reason,
        bool bWasClean
    );

    TSharedPtr<IWebSocket> Socket;
    TSharedPtr<FSarembokMessageDispatcher> Dispatcher;

    FString ServerURL;
    FString AuthToken;
    bool bAutoReconnect;
};
