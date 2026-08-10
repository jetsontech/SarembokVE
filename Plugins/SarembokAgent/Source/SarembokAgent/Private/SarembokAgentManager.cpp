#include "SarembokAgentManager.h"
#include "SarembokDeterministicReasoner.h"
#include "SarembokLLMReasoner.h"
#include "SarembokVisionManager.h"
#include "SarembokMemorySubsystem.h"
#include "SarembokEpisode.h"
#include "SarembokMessageDispatcher.h"
#include "Misc/DateTime.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"

void USarembokAgentManager::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    CurrentState = ESarembokAgentState::Idle;
    ActiveTask = FSarembokTask();
    LoopCounter = 0;
    IdleCycleCounter = 0;
    GoalStack.Empty();
    bSimulateFailure = false;

    // Initialize with deterministic reasoning provider by default
    ReasoningProvider = MakeUnique<FSarembokDeterministicReasoner>();

    // Register ticker to run autonomous perception loop periodically (every 1.5 seconds)
    TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateUObject(this, &USarembokAgentManager::ProcessAutonomousTick),
        1.5f
    );

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][AGENT] Runtime Initialized | Provider=%s | Ticker=Active"),
        *ReasoningProvider->GetProviderName());
}

void USarembokAgentManager::Deinitialize()
{
    CurrentState = ESarembokAgentState::Shutdown;

    if (TickerHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(TickerHandle);
        TickerHandle.Reset();
    }

    ReasoningProvider.Reset();
    GoalStack.Empty();
    Super::Deinitialize();
}

bool USarembokAgentManager::ProcessAutonomousTick(float DeltaTime)
{
    if (IsEngineExitRequested())
    {
        return false;
    }

    FString GeneratedCommand;
    if (RunAutonomousLoop(GeneratedCommand) && !GeneratedCommand.IsEmpty())
    {
        // Dispatch autonomous command through the Bridge dispatcher
        static FSarembokMessageDispatcher AgentDispatcher;
        AgentDispatcher.DispatchMessage(GeneratedCommand);
    }

    return true;
}

FString USarembokAgentManager::SubmitTask(const FSarembokTask& Task)
{
    ActiveTask = Task;
    CurrentState = ESarembokAgentState::Perceive;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][AGENT] TASK SUBMITTED | TaskId=%s | Intent=%s"),
        *Task.TaskId,
        *Task.Intent
    );

    return ActiveTask.TaskId;
}

// ---- v1.3 Goal Stack Implementation ----

void USarembokAgentManager::PushGoal(const FSarembokGoal& Goal)
{
    FSarembokGoal NewGoal = Goal;
    if (NewGoal.GoalId.IsEmpty())
    {
        NewGoal.GoalId = FString::Printf(TEXT("goal-%06d"), GoalStack.Num() + 1);
    }

    GoalStack.Push(NewGoal);

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][AGENT] GOAL_PUSHED | GoalId=%s | Desc=%s | Priority=%d | Total=%d"),
        *NewGoal.GoalId, *NewGoal.Description, NewGoal.Priority, GoalStack.Num());
}

bool USarembokAgentManager::PopGoal(FSarembokGoal& OutGoal)
{
    if (GoalStack.IsEmpty())
    {
        OutGoal = FSarembokGoal();
        return false;
    }

    OutGoal = GoalStack.Pop();

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][AGENT] GOAL_POPPED | GoalId=%s | Status=%s | Remaining=%d"),
        *OutGoal.GoalId, *OutGoal.Status, GoalStack.Num());

    return true;
}

FSarembokGoal USarembokAgentManager::GetActiveGoal() const
{
    if (GoalStack.IsEmpty())
    {
        return FSarembokGoal();
    }
    return GoalStack.Last();
}

bool USarembokAgentManager::CompleteActiveGoal()
{
    if (GoalStack.IsEmpty())
    {
        return false;
    }

    FSarembokGoal Completed = GoalStack.Pop();
    Completed.Status = TEXT("Completed");
    Completed.Progress = 1.0f;

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][AGENT] GOAL_COMPLETED | GoalId=%s | Desc=%s"),
        *Completed.GoalId, *Completed.Description);

    return true;
}

bool USarembokAgentManager::FailActiveGoal(const FString& Reason)
{
    if (GoalStack.IsEmpty())
    {
        return false;
    }

    FSarembokGoal FailedGoal = GoalStack.Pop();
    FailedGoal.Status = TEXT("Failed");

    UE_LOG(LogTemp, Warning,
        TEXT("[SAREMBOK][AGENT] GOAL_FAILED | GoalId=%s | Reason=%s"),
        *FailedGoal.GoalId, *Reason);

    return true;
}

int32 USarembokAgentManager::GetGoalCount() const
{
    return GoalStack.Num();
}

// ---- v1.3 Reasoner Controls ----

void USarembokAgentManager::SetReasoningProvider(TUniquePtr<ISarembokReasoningProvider> NewProvider)
{
    if (NewProvider.IsValid())
    {
        ReasoningProvider = MoveTemp(NewProvider);

        UE_LOG(LogTemp, Display,
            TEXT("[SAREMBOK][AGENT] REASONER_REGISTERED | Provider=%s"),
            *ReasoningProvider->GetProviderName());
    }
}

void USarembokAgentManager::SetLLMMode(bool bEnableLLM)
{
    SetReasoningProvider(MakeUnique<FSarembokLLMReasoner>(bEnableLLM));
}

FString USarembokAgentManager::GetActiveProviderName() const
{
    return ReasoningProvider.IsValid() ? ReasoningProvider->GetProviderName() : TEXT("None");
}

void USarembokAgentManager::SetSimulateActionFailure(bool bSimulate)
{
    bSimulateFailure = bSimulate;

    if (bSimulateFailure)
    {
        UE_LOG(LogTemp, Warning, TEXT("[SAREMBOK][AGENT] SIMULATED_ACTION_FAILURE_ENABLED"));
    }
}

// ---- Full Perception-Action-Replanning Cycle ----

bool USarembokAgentManager::RunAutonomousLoop(FString& OutGeneratedCommand)
{
    LoopCounter++;
    FString TraceId = FString::Printf(TEXT("trace-%06d"), LoopCounter);
    FString CmdId = FString::Printf(TEXT("cmd-%06d"), LoopCounter);
    FString Timestamp = FDateTime::UtcNow().ToIso8601();

    UGameInstance* GI = GetGameInstance();
    if (!GI)
    {
        return false;
    }

    // Get subsystem references
    USarembokVisionManager* Vision = GI->GetSubsystem<USarembokVisionManager>();
    USarembokMemorySubsystem* Memory = GI->GetSubsystem<USarembokMemorySubsystem>();

    if (!Vision || !Memory)
    {
        UE_LOG(LogTemp, Warning,
            TEXT("[SAREMBOK][AGENT] Cannot run loop: Vision or Memory subsystem unavailable"));
        return false;
    }

    FSarembokGoal ActiveGoal = GetActiveGoal();

    // ---- PERCEIVE ----
    TransitionState(ESarembokAgentState::Perceive, TraceId);
    FSarembokWorldState WorldState = Vision->GetWorldState();

    // Store current world state snapshot & goal in working memory
    Memory->SetWorkingMemory(TEXT("world_actor_count"), FString::FromInt(WorldState.ActorCount));
    Memory->SetWorkingMemory(TEXT("world_timestamp"), WorldState.Timestamp.ToIso8601());
    if (!ActiveGoal.GoalId.IsEmpty())
    {
        Memory->SetWorkingMemory(TEXT("active_goal_id"), ActiveGoal.GoalId);
        Memory->SetWorkingMemory(TEXT("active_goal_desc"), ActiveGoal.Description);
    }

    // ---- INTERPRET ----
    TransitionState(ESarembokAgentState::Interpret, TraceId);
    FSarembokWorldDelta Delta = Vision->DetectChanges();

    // ---- RECALL ----
    TransitionState(ESarembokAgentState::Recall, TraceId);
    TArray<FSarembokEpisode> RecentEpisodes = Memory->RecallRecentEpisodes(5);

    // ---- PLAN ----
    TransitionState(ESarembokAgentState::Plan, TraceId);

    if (!Delta.bHasChanges)
    {
        IdleCycleCounter++;
    }
    else
    {
        IdleCycleCounter = 0;
    }

    FSarembokIntent Intent = ReasoningProvider->ReasonWithGoal(Delta, ActiveGoal, RecentEpisodes, IdleCycleCounter);

    if (!Intent.bShouldAct)
    {
        TransitionState(ESarembokAgentState::Idle, TraceId);

        UE_LOG(LogTemp, Display,
            TEXT("[SAREMBOK][AGENT] NO_ACTION | TraceId=%s | Reason=%s"),
            *TraceId, *Intent.Reason);

        return false;
    }

    // ---- SELECT_ACTION ----
    TransitionState(ESarembokAgentState::SelectAction, TraceId);

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][AGENT] INTENT_GENERATED | TraceId=%s | Action=%s | Confidence=%.2f | GoalId=%s | Reason=%s"),
        *TraceId, *Intent.ActionType, Intent.Confidence, *Intent.GoalId, *Intent.Reason);

    // ---- EXECUTE ----
    TransitionState(ESarembokAgentState::Execute, TraceId);

    // Build sarembok.v1 command envelope
    FString PayloadJson;
    if (Intent.ActionType.Equals(TEXT("Speak"), ESearchCase::IgnoreCase))
    {
        PayloadJson = FString::Printf(
            TEXT("{\"text\":\"%s\",\"emotion\":\"%s\"}"),
            *Intent.SpeechText,
            *Intent.EmotionState
        );
    }
    else if (Intent.ActionType.Equals(TEXT("Emotion"), ESearchCase::IgnoreCase))
    {
        PayloadJson = FString::Printf(
            TEXT("{\"state\":\"%s\"}"),
            *Intent.EmotionState
        );
    }
    else
    {
        PayloadJson = TEXT("{}");
    }

    OutGeneratedCommand = FString::Printf(
        TEXT("{\"protocol\":\"sarembok.v1\",\"id\":\"%s\",\"timestamp\":\"%s\",\"command\":\"%s\",\"target\":\"%s\",\"payload\":%s,\"context\":{\"agent\":\"%s\",\"trace\":\"%s\",\"confidence\":%.2f,\"goal_id\":\"%s\",\"reason\":\"%s\"}}"),
        *CmdId,
        *Timestamp,
        *Intent.ActionType,
        *Intent.Target,
        *PayloadJson,
        *ReasoningProvider->GetProviderName(),
        *TraceId,
        Intent.Confidence,
        *Intent.GoalId,
        *Intent.Reason
    );

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][AGENT] REASONING_LOOP | Id=%s | TraceId=%s | LoopTick=%d | Action=%s | Confidence=%.2f"),
        *CmdId, *TraceId, LoopCounter, *Intent.ActionType, Intent.Confidence);

    // ---- OBSERVE_RESULT ----
    TransitionState(ESarembokAgentState::ObserveResult, TraceId);

    // ---- EVALUATE ----
    TransitionState(ESarembokAgentState::Evaluate, TraceId);

    bool bOutcomeSuccess = !bSimulateFailure;

    if (!bOutcomeSuccess)
    {
        // Failure recovery replanning triggered
        TransitionState(ESarembokAgentState::Replan, TraceId);

        UE_LOG(LogTemp, Warning,
            TEXT("[SAREMBOK][AGENT] REPLAN_TRIGGERED | TraceId=%s | Reason=Action outcome failure simulated | Candidates=%d"),
            *TraceId, Intent.AlternativeActions.Num());

        // Attempt alternative action or fallback
        if (Intent.AlternativeActions.Num() > 0)
        {
            FString RetryAction = Intent.AlternativeActions[0];
            UE_LOG(LogTemp, Display,
                TEXT("[SAREMBOK][AGENT] REPLAN_RETRY_ACTION | TraceId=%s | SelectedAlternative=%s"),
                *TraceId, *RetryAction);
        }

        // Reset test trigger flag after logging
        bSimulateFailure = false;

        // Record failed episode
        FSarembokEpisode FailedEpisode;
        FailedEpisode.Timestamp = FDateTime::UtcNow();
        FailedEpisode.EventType = Intent.ActionType;
        FailedEpisode.Description = FString::Printf(TEXT("REPLAN: %s"), *Intent.Reason);
        FailedEpisode.ActionTaken = OutGeneratedCommand;
        FailedEpisode.Outcome = TEXT("replanned_failure");
        FailedEpisode.TraceId = TraceId;
        Memory->StoreEpisode(FailedEpisode);

        TransitionState(ESarembokAgentState::Failed, TraceId);
        return true;
    }

    // Record successful episode
    FSarembokEpisode Episode;
    Episode.Timestamp = FDateTime::UtcNow();
    Episode.EventType = Intent.ActionType;
    Episode.Description = Intent.Reason;
    Episode.ActionTaken = OutGeneratedCommand;
    Episode.Outcome = TEXT("dispatched");
    Episode.TraceId = TraceId;

    if (Delta.Deltas.Num() > 0)
    {
        Episode.ActorId = Delta.Deltas[0].Actor.ActorId;
    }

    Memory->StoreEpisode(Episode);

    TransitionState(ESarembokAgentState::Completed, TraceId);

    return true;
}

FString USarembokAgentManager::GetAgentState() const
{
    return StateToString(CurrentState);
}

FSarembokTask USarembokAgentManager::GetActiveTask() const
{
    return ActiveTask;
}

void USarembokAgentManager::CancelCurrentTask()
{
    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][AGENT] TASK CANCELLED | TaskId=%s"),
        *ActiveTask.TaskId
    );

    ActiveTask = FSarembokTask();
    CurrentState = ESarembokAgentState::Idle;
}

void USarembokAgentManager::TransitionState(ESarembokAgentState NewState, const FString& TraceId)
{
    FString OldStateName = StateToString(CurrentState);
    FString NewStateName = StateToString(NewState);
    CurrentState = NewState;

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][AGENT] STATE | %s -> %s | TraceId=%s"),
        *OldStateName, *NewStateName, *TraceId);
}

FString USarembokAgentManager::StateToString(ESarembokAgentState State)
{
    switch (State)
    {
    case ESarembokAgentState::Idle:          return TEXT("IDLE");
    case ESarembokAgentState::Perceive:      return TEXT("PERCEIVE");
    case ESarembokAgentState::Interpret:     return TEXT("INTERPRET");
    case ESarembokAgentState::Recall:        return TEXT("RECALL");
    case ESarembokAgentState::Plan:          return TEXT("PLAN");
    case ESarembokAgentState::SelectAction:  return TEXT("SELECT_ACTION");
    case ESarembokAgentState::Execute:       return TEXT("EXECUTE");
    case ESarembokAgentState::ObserveResult: return TEXT("OBSERVE_RESULT");
    case ESarembokAgentState::Evaluate:      return TEXT("EVALUATE");
    case ESarembokAgentState::Replan:        return TEXT("REPLAN");
    case ESarembokAgentState::Completed:     return TEXT("COMPLETED");
    case ESarembokAgentState::Failed:        return TEXT("FAILED");
    case ESarembokAgentState::Shutdown:       return TEXT("SHUTDOWN");
    default:                                 return TEXT("UNKNOWN");
    }
}
