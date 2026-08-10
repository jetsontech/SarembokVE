#include "SarembokAgentManager.h"
#include "Misc/DateTime.h"

void USarembokAgentManager::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    CurrentState = TEXT("Idle");
    ActiveTask = FSarembokTask();
    LoopCounter = 0;

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][AGENT] Runtime Initialized"));
}

void USarembokAgentManager::Deinitialize()
{
    CurrentState = TEXT("Shutdown");
    Super::Deinitialize();
}

FString USarembokAgentManager::SubmitTask(const FSarembokTask& Task)
{
    ActiveTask = Task;
    CurrentState = TEXT("Executing");

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][AGENT] TASK SUBMITTED | TaskId=%s | Intent=%s"),
        *Task.TaskId,
        *Task.Intent
    );

    return ActiveTask.TaskId;
}

bool USarembokAgentManager::RunAutonomousLoop(FString& OutGeneratedCommand)
{
    LoopCounter++;
    CurrentState = TEXT("Reasoning");

    FString CmdId = FString::Printf(TEXT("cmd-%06d"), LoopCounter);
    FString Timestamp = FDateTime::UtcNow().ToIso8601();

    // Formulate versioned sarembok.v1 command JSON envelope
    OutGeneratedCommand = FString::Printf(
        TEXT("{\"protocol\":\"sarembok.v1\",\"id\":\"%s\",\"timestamp\":\"%s\",\"command\":\"Speak\",\"target\":\"Avatar\",\"payload\":{\"text\":\"Autonomous perception loop tick %d\",\"emotion\":\"Joyful\"},\"context\":{\"agent\":\"SarembokAgent\",\"task\":\"%s\"}}"),
        *CmdId,
        *Timestamp,
        LoopCounter,
        *ActiveTask.TaskId
    );

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][AGENT] REASONING_LOOP | Id=%s | LoopTick=%d | TaskId=%s"),
        *CmdId,
        LoopCounter,
        *ActiveTask.TaskId
    );

    CurrentState = TEXT("Executing");
    return true;
}

FString USarembokAgentManager::GetAgentState() const
{
    return CurrentState;
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
    CurrentState = TEXT("Idle");
}
