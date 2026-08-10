#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"

class SAREMBOKBRIDGE_API FSarembokMessageDispatcher
{
public:
    FSarembokMessageDispatcher();
    ~FSarembokMessageDispatcher();

    void DispatchMessage(const FString& Message);

    FString GetLastCommand() const;
    FString GetLastProtocol() const;
    FString GetLastCorrelationId() const;

private:
    void ParseCommand(const FString& Message);
    bool ExecuteCommand(const FString& Message);
    bool ProcessQueuedCommands(float DeltaTime);

    FString LastProtocol;
    FString LastId;
    FString LastTimestamp;
    FString LastCommand;
    FString LastTarget;
    FString LastPayload;

    TArray<FString> PendingCommands;
    FTSTicker::FDelegateHandle QueueTickerHandle;
};
