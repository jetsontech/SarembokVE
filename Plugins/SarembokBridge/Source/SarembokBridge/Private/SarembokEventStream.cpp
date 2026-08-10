// ============================================================
// SarembokEventStream.cpp
// Unified Event Sourcing & Trajectory Logging Implementation
// ============================================================

#include "SarembokEventStream.h"

void USarembokEventStreamSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    EventStream.Empty();
    EventCounter = 0;

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][EVENT_STREAM] INITIALIZED"));
}

void USarembokEventStreamSubsystem::Deinitialize()
{
    EventStream.Empty();
    Super::Deinitialize();
}

void USarembokEventStreamSubsystem::EmitEvent(const FSarembokEvent& Event)
{
    EventCounter++;
    FSarembokEvent RecordedEvent = Event;
    if (RecordedEvent.EventId.IsEmpty())
    {
        RecordedEvent.EventId = FString::Printf(TEXT("evt-%06d"), EventCounter);
    }

    EventStream.Add(RecordedEvent);

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][EVENT_STREAM] EVENT_SOURCED | Id=%s | Type=%s | Source=%s | TraceId=%s | UserId=%s | ConvId=%s"),
        *RecordedEvent.EventId, *RecordedEvent.EventType, *RecordedEvent.Source,
        *RecordedEvent.TraceId, *RecordedEvent.UserId, *RecordedEvent.ConversationId);
}

TArray<FSarembokEvent> USarembokEventStreamSubsystem::QueryEventsByTraceId(const FString& TraceId) const
{
    TArray<FSarembokEvent> Results;
    for (const FSarembokEvent& Evt : EventStream)
    {
        if (Evt.TraceId.Equals(TraceId, ESearchCase::IgnoreCase))
        {
            Results.Add(Evt);
        }
    }
    return Results;
}

TArray<FSarembokEvent> USarembokEventStreamSubsystem::QueryEventsByUserId(const FString& UserId) const
{
    TArray<FSarembokEvent> Results;
    for (const FSarembokEvent& Evt : EventStream)
    {
        if (Evt.UserId.Equals(UserId, ESearchCase::IgnoreCase))
        {
            Results.Add(Evt);
        }
    }
    return Results;
}

int32 USarembokEventStreamSubsystem::GetEventCount() const
{
    return EventStream.Num();
}
