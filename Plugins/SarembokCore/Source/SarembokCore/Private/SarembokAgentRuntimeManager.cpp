// ============================================================
// SarembokAgentRuntimeManager.cpp
// Multi-Agent Runtime Manager Subsystem — Sarembok_VE v2.1
// ============================================================
#include "SarembokAgentRuntimeManager.h"

void USarembokAgentRuntimeManager::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][RUNTIME_MANAGER] Runtime Manager ONLINE | v2.1"));
}

bool USarembokAgentRuntimeManager::RegisterAgentRuntime(const FString& AgentId, const FString& RoleName)
{
    ActiveAgentRoles.Add(AgentId, RoleName);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][RUNTIME_MANAGER] Agent runtime registered | AgentId=%s | Role=%s"), *AgentId, *RoleName);
    return true;
}

bool USarembokAgentRuntimeManager::IsAgentActive(const FString& AgentId) const
{
    return ActiveAgentRoles.Contains(AgentId);
}

TArray<FString> USarembokAgentRuntimeManager::GetActiveAgentRuntimes() const
{
    TArray<FString> Result;
    ActiveAgentRoles.GetKeys(Result);
    return Result;
}

bool USarembokAgentRuntimeManager::TerminateAgentRuntime(const FString& AgentId)
{
    if (ActiveAgentRoles.Contains(AgentId))
    {
        ActiveAgentRoles.Remove(AgentId);
        UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][RUNTIME_MANAGER] Agent runtime terminated | AgentId=%s"), *AgentId);
        return true;
    }
    return false;
}
