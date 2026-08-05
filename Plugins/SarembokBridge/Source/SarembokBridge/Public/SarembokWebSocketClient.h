#pragma once

#include "CoreMinimal.h"
#include "IWebSocket.h"

class FSarembokWebSocketClient
{
public:

    FSarembokWebSocketClient();

    ~FSarembokWebSocketClient();

    void Connect();

    void Disconnect();

    void SendMessage(const FString& Message);

    bool IsConnected() const { return bConnected; }

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

    FString ServerURL;

    bool bConnected = false;
};
