#include "SarembokAgentManager.h"

void USarembokAgentManager::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    CurrentState = TEXT("Idle");
    ActiveTask = FSarembokTask();

    UE_LOG(LogTemp, Display, TEXT("Sarembok Agent Runtime Initialized"));
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
        TEXT("[SAREMBOK] AGENT TASK SUBMITTED | TaskId=%s | Intent=%s"),
        *Task.TaskId,
        *Task.Intent
    );

    return ActiveTask.TaskId;
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
        TEXT("[SAREMBOK] AGENT TASK CANCELLED | TaskId=%s"),
        *ActiveTask.TaskId
    );

    ActiveTask = FSarembokTask();
    CurrentState = TEXT("Idle");
}
