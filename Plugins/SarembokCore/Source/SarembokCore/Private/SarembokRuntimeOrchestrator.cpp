// ============================================================
// SarembokRuntimeOrchestrator.cpp
// Unified Cognitive Cycle Orchestrator — Sarembok_VE v2.0
// ============================================================
#include "SarembokRuntimeOrchestrator.h"

void USarembokRuntimeOrchestrator::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][ORCHESTRATOR] Unified Runtime Orchestrator ONLINE | v2.0"));
}

void USarembokRuntimeOrchestrator::Deinitialize()
{
    ActiveCycles.Empty();
    Super::Deinitialize();
}

void USarembokRuntimeOrchestrator::StartCognitiveCycle(const FString& AgentId)
{
    if (!ActiveCycles.Contains(AgentId))
    {
        FSarembokCognitiveCycleState State;
        State.AgentId              = AgentId;
        State.Stage                = ECognitiveCycleStage::Idle;
        State.CycleStartTimeMs     = 0.0f;
        State.LastCycleDurationMs  = 0.0f;
        State.TotalCyclesCompleted = 0;
        State.bCycleActive         = true;
        ActiveCycles.Add(AgentId, State);
    }
    else
    {
        ActiveCycles[AgentId].bCycleActive = true;
    }

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][ORCHESTRATOR] Cognitive cycle STARTED | AgentId=%s"), *AgentId);
    AdvanceCycle(AgentId);
}

void USarembokRuntimeOrchestrator::StopCognitiveCycle(const FString& AgentId)
{
    if (ActiveCycles.Contains(AgentId))
    {
        ActiveCycles[AgentId].bCycleActive = false;
        UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][ORCHESTRATOR] Cognitive cycle STOPPED | AgentId=%s"), *AgentId);
    }
}

void USarembokRuntimeOrchestrator::AdvanceCycle(const FString& AgentId)
{
    if (!ActiveCycles.Contains(AgentId)) return;
    FSarembokCognitiveCycleState& State = ActiveCycles[AgentId];
    if (!State.bCycleActive) return;

    static const TArray<ECognitiveCycleStage> Pipeline = {
        ECognitiveCycleStage::Vision,
        ECognitiveCycleStage::MemoryRetrieval,
        ECognitiveCycleStage::ContextBuilding,
        ECognitiveCycleStage::Reasoning,
        ECognitiveCycleStage::GoalSelection,
        ECognitiveCycleStage::PolicyEvaluation,
        ECognitiveCycleStage::ActionDispatch,
        ECognitiveCycleStage::Evaluation,
        ECognitiveCycleStage::Learning,
        ECognitiveCycleStage::Persist,
        ECognitiveCycleStage::Idle
    };

    int32 CurrentIdx = Pipeline.IndexOfByKey(State.Stage);
    int32 NextIdx = (CurrentIdx < 0) ? 0 : FMath::Min(CurrentIdx + 1, Pipeline.Num() - 1);

    TransitionStage(State, Pipeline[NextIdx]);

    if (Pipeline[NextIdx] == ECognitiveCycleStage::Idle)
    {
        State.TotalCyclesCompleted++;
    }
}

FSarembokCognitiveCycleState USarembokRuntimeOrchestrator::GetCycleState(const FString& AgentId) const
{
    const FSarembokCognitiveCycleState* Found = ActiveCycles.Find(AgentId);
    return Found ? *Found : FSarembokCognitiveCycleState{};
}

TArray<FString> USarembokRuntimeOrchestrator::GetActiveAgentIds() const
{
    TArray<FString> Ids;
    ActiveCycles.GetKeys(Ids);
    return Ids;
}

void USarembokRuntimeOrchestrator::TransitionStage(FSarembokCognitiveCycleState& State, ECognitiveCycleStage Next)
{
    State.Stage = Next;
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][ORCHESTRATOR] Cycle stage → %s | AgentId=%s | Cycles=%d"),
        *StageToString(Next), *State.AgentId, State.TotalCyclesCompleted);
}

FString USarembokRuntimeOrchestrator::StageToString(ECognitiveCycleStage Stage) const
{
    switch (Stage)
    {
        case ECognitiveCycleStage::Vision:           return TEXT("VISION");
        case ECognitiveCycleStage::MemoryRetrieval:  return TEXT("MEMORY_RETRIEVAL");
        case ECognitiveCycleStage::ContextBuilding:  return TEXT("CONTEXT_BUILDING");
        case ECognitiveCycleStage::Reasoning:        return TEXT("REASONING");
        case ECognitiveCycleStage::GoalSelection:    return TEXT("GOAL_SELECTION");
        case ECognitiveCycleStage::PolicyEvaluation: return TEXT("POLICY_EVALUATION");
        case ECognitiveCycleStage::ActionDispatch:   return TEXT("ACTION_DISPATCH");
        case ECognitiveCycleStage::Evaluation:       return TEXT("EVALUATION");
        case ECognitiveCycleStage::Learning:         return TEXT("LEARNING");
        case ECognitiveCycleStage::Persist:          return TEXT("PERSIST");
        case ECognitiveCycleStage::Idle:             return TEXT("IDLE");
        default:                                      return TEXT("UNKNOWN");
    }
}
