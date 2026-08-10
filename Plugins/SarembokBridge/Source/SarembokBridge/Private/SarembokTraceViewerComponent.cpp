// ============================================================
// SarembokTraceViewerComponent.cpp
// Cognitive Trace Timeline Inspector Component Implementation
// ============================================================

#include "SarembokTraceViewerComponent.h"

USarembokTraceViewerComponent::USarembokTraceViewerComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void USarembokTraceViewerComponent::BeginPlay()
{
    Super::BeginPlay();
    ActiveTimeline.Empty();
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][TRACE_VIEWER] INITIALIZED"));
}

void USarembokTraceViewerComponent::LogTraceStep(const FString& Stage, const FString& Message)
{
    FSarembokTraceStep Step;
    Step.TimestampMs = FPlatformTime::Seconds() * 1000.0;
    Step.Stage = Stage;
    Step.Message = Message;
    ActiveTimeline.Add(Step);

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][TRACE] %s | %s"),
        *Stage, *Message);
}

void USarembokTraceViewerComponent::FormatAndEmitTimeline(const FString& TraceId)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][TRACE_VIEWER] TIMELINE_EMITTED | TraceId=%s | Steps=%d"), *TraceId, ActiveTimeline.Num());
}
