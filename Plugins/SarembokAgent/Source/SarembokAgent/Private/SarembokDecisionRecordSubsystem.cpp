// ============================================================
// SarembokDecisionRecordSubsystem.cpp
// Structured Cognitive Decision Record Subsystem Implementation
// ============================================================

#include "SarembokDecisionRecordSubsystem.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void USarembokDecisionRecordSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    DecisionHistory.Empty();

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][DECISION_RECORD] INITIALIZED"));
}

void USarembokDecisionRecordSubsystem::Deinitialize()
{
    Super::Deinitialize();
}

void USarembokDecisionRecordSubsystem::RecordDecision(const FSarembokDecisionRecord& Record)
{
    DecisionHistory.Add(Record);

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][DECISION_RECORD] RECORDED | DecisionId=%s | TraceId=%s | Action=%s | Policy=%s | Outcome=%s"),
        *Record.DecisionId, *Record.TraceId, *Record.SelectedAction, *Record.PolicyResult, *Record.Outcome);
}

TArray<FSarembokDecisionRecord> USarembokDecisionRecordSubsystem::GetRecentDecisionRecords(int32 MaxCount) const
{
    TArray<FSarembokDecisionRecord> Recent;
    int32 StartIndex = FMath::Max(0, DecisionHistory.Num() - MaxCount);
    for (int32 i = StartIndex; i < DecisionHistory.Num(); ++i)
    {
        Recent.Add(DecisionHistory[i]);
    }
    return Recent;
}
