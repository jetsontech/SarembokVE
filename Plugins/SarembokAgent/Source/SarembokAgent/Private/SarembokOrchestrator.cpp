#include "SarembokOrchestrator.h"

void USarembokOrchestrator::StartInteraction(const FString& Context)
{
    CurrentOperation = FString::Printf(TEXT("PROCESSING:%s"), *Context);

    UE_LOG(LogTemp, Log,
        TEXT("Sarembok Orchestrator started: %s"),
        *Context);
}

FString USarembokOrchestrator::GetCurrentOperation() const
{
    return CurrentOperation;
}
