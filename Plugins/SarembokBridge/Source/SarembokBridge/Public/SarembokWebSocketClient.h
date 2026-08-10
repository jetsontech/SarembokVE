#pragma once

#include "CoreMinimal.h"
#include "IWebSocket.h"

DECLARE_MULTICAST_DELEGATE_OneParam(FSarembokWebSocketMessageDelegate, const FString&);

class FSarembokWebSocketClient
{
public:
    FSarembokWebSocketClient();
    ~FSarembokWebSocketClient();

    void Connect();
    void Disconnect();
    void SendMessage(const FString& Message);

    FSarembokWebSocketMessageDelegate& OnMessageReceived()
    {
        return MessageReceived;
    }

private:
    void OnConnected();
    void OnMessage(const FString& Message);
    void OnConnectionError(const FString& Error);
    void OnClosed(int32 StatusCode, const FString& Reason, bool bWasClean);

    TSharedPtr<IWebSocket> Socket;
    FString ServerURL;
    FSarembokWebSocketMessageDelegate MessageReceived;
};
