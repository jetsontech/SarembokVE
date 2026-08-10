#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"

class FSarembokMessageDispatcher
{
public:
    FSarembokMessageDispatcher();
    ~FSarembokMessageDispatcher();

    void DispatchMessage(const FString& Message);

    FString GetLastCommand() const;

private:
    void ParseCommand(const FString& Message);
    bool ExecuteCommand(const FString& Message);
    bool ProcessQueuedCommands(float DeltaTime);

    FString LastCommand;
    FString LastTarget;
    FString LastPayload;

    TArray<FString> PendingCommands;
    FTSTicker::FDelegateHandle QueueTickerHandle;
};
