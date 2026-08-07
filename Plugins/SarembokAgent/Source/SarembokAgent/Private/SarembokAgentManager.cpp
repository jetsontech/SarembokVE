#include "SarembokAgentManager.h"

void USarembokAgentManager::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    CurrentState = TEXT("READY");

    UE_LOG(LogTemp, Log, TEXT("Sarembok Agent Runtime Initialized"));
}

void USarembokAgentManager::Deinitialize()
{
    CurrentState = TEXT("OFFLINE");
    Super::Deinitialize();
}

FString USarembokAgentManager::SubmitTask(const FSarembokTask& Task)
{
    CurrentState = FString::Printf(TEXT("EXECUTING:%s"), *Task.Intent);

    UE_LOG(LogTemp, Log,
        TEXT("Sarembok Task [%s] Payload [%s]"),
        *Task.Intent,
        *Task.Payload);

    return CurrentState;
}

FString USarembokAgentManager::GetAgentState() const
{
    return CurrentState;
}
