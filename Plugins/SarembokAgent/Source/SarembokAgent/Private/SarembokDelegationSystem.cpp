// ============================================================
// SarembokDelegationSystem.cpp
// Event-Driven Task Delegation System — Sarembok_VE v2.1
// ============================================================
#include "SarembokDelegationSystem.h"
#include "Misc/Guid.h"

void USarembokDelegationSystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][DELEGATION] Task Delegation Subsystem ONLINE | v2.1"));
}

FSarembokDelegationRecord USarembokDelegationSystem::CreateDelegation(
    const FString& SourceAgentId, const FString& TargetAgentId,
    const FString& GoalId, const FString& RequiredCapability)
{
    FSarembokDelegationRecord Record;
    Record.DelegationId       = FString::Printf(TEXT("del-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    Record.SourceAgentId      = SourceAgentId;
    Record.TargetAgentId      = TargetAgentId;
    Record.GoalId             = GoalId;
    Record.RequiredCapability = RequiredCapability;
    Record.Status             = EDelegationStatus::Created;
    Record.RetryCount         = 0;
    Record.Timestamp          = FDateTime::UtcNow().ToString();

    Delegations.Add(Record.DelegationId, Record);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][DELEGATION] Created delegation | DelId=%s | Src=%s | Tgt=%s | Cap=%s"),
        *Record.DelegationId, *SourceAgentId, *TargetAgentId, *RequiredCapability);

    return Record;
}

bool USarembokDelegationSystem::UpdateDelegationStatus(const FString& DelegationId, EDelegationStatus NewStatus, const FString& ResultData)
{
    if (FSarembokDelegationRecord* Found = Delegations.Find(DelegationId))
    {
        Found->Status     = NewStatus;
        Found->ResultData = ResultData;
        Found->Timestamp  = FDateTime::UtcNow().ToString();

        UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][DELEGATION] Status updated | DelId=%s | NewStatus=%d"), *DelegationId, (int32)NewStatus);
        return true;
    }
    return false;
}

FSarembokDelegationRecord USarembokDelegationSystem::GetDelegation(const FString& DelegationId) const
{
    const FSarembokDelegationRecord* Found = Delegations.Find(DelegationId);
    return Found ? *Found : FSarembokDelegationRecord{};
}

bool USarembokDelegationSystem::ReassignDelegation(const FString& DelegationId, const FString& NewTargetAgentId)
{
    if (FSarembokDelegationRecord* Found = Delegations.Find(DelegationId))
    {
        Found->TargetAgentId = NewTargetAgentId;
        Found->Status        = EDelegationStatus::Reassigned;
        Found->RetryCount++;
        Found->Timestamp     = FDateTime::UtcNow().ToString();

        UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][DELEGATION] Reassigned | DelId=%s | NewTgt=%s | RetryCount=%d"),
            *DelegationId, *NewTargetAgentId, Found->RetryCount);
        return true;
    }
    return false;
}
