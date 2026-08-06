#pragma once

#include "CoreMinimal.h"
#include "IWebSocket.h"

class FSarembokWebSocket
{
public:
    FSarembokWebSocket();
    ~FSarembokWebSocket();

    void Connect();
    void Disconnect();
    bool IsConnected() const;
    void SendMessage(const FString& Message);

private:
    TSharedPtr<IWebSocket> Socket;
};
