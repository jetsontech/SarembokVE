#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"

// ---- v1.2 Execution Trace ----

struct FSarembokTraceEvent
{
    FString Subsystem;    // "VISION", "MEMORY", "AGENT", "BRIDGE", "AVATAR", "VOICE"
    FString EventName;    // "WORLD_STATE", "EPISODE_STORED", "INTENT_GENERATED", etc.
    FString CorrelationId;
    FString PayloadSnapshot;
    FDateTime Timestamp;
    double DurationMs = 0.0;
};

struct FSarembokExecutionTrace
{
    FString TraceId;
    FDateTime StartTime;
    FDateTime EndTime;
    TArray<FSarembokTraceEvent> Events;
    bool bComplete = false;

    void AddEvent(const FString& Subsystem, const FString& EventName,
                  const FString& CorrelationId, const FString& Payload = TEXT(""))
    {
        FSarembokTraceEvent Event;
        Event.Subsystem = Subsystem;
        Event.EventName = EventName;
        Event.CorrelationId = CorrelationId;
        Event.PayloadSnapshot = Payload;
        Event.Timestamp = FDateTime::UtcNow();
        Events.Add(Event);
    }

    void Complete()
    {
        EndTime = FDateTime::UtcNow();
        bComplete = true;
    }
};

// ---- Message Dispatcher ----

class SAREMBOKBRIDGE_API FSarembokMessageDispatcher
{
public:
    FSarembokMessageDispatcher();
    ~FSarembokMessageDispatcher();

    void DispatchMessage(const FString& Message);

    FString GetLastCommand() const;
    FString GetLastProtocol() const;
    FString GetLastCorrelationId() const;

    // v1.2 trace system
    const TArray<FSarembokExecutionTrace>& GetTraces() const;
    TArray<FSarembokExecutionTrace> GetRecentTraces(int32 Count) const;

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

    // v1.2 trace storage
    TArray<FSarembokExecutionTrace> ExecutionTraces;
    static constexpr int32 MaxTraces = 128;

    FString ExtractTraceId(const FString& Message) const;
};
