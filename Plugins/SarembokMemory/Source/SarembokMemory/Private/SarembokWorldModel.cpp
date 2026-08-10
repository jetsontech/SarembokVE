// ============================================================
// SarembokWorldModel.cpp
// Persistent World Model & Epistemic Belief Tracking — Sarembok VE 3.0
// ============================================================
#include "SarembokWorldModel.h"
#include "Misc/Guid.h"

void USarembokWorldModel::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][WORLD_MODEL] SarembokWorldModel Subsystem ONLINE | v3.0"));
}

void USarembokWorldModel::UpsertEntity(const FSarembokWorldEntity& Entity)
{
    FSarembokWorldEntity Ent = Entity;
    if (Ent.Timestamp.IsEmpty())
    {
        Ent.Timestamp = FDateTime::UtcNow().ToString();
    }
    Entities.Add(Ent.EntityId, Ent);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][WORLD_MODEL] Upserted entity | Id=%s | Name=%s | Type=%d"),
        *Ent.EntityId, *Ent.Name, (int32)Ent.EntityType);
}

FSarembokWorldEntity USarembokWorldModel::GetEntity(const FString& EntityId) const
{
    const FSarembokWorldEntity* Found = Entities.Find(EntityId);
    return Found ? *Found : FSarembokWorldEntity{};
}

TArray<FSarembokWorldEntity> USarembokWorldModel::GetAllEntities() const
{
    TArray<FSarembokWorldEntity> Result;
    Entities.GenerateValueArray(Result);
    return Result;
}

void USarembokWorldModel::RegisterBelief(const FSarembokAgentBelief& Belief)
{
    FSarembokAgentBelief B = Belief;
    if (B.BeliefId.IsEmpty())
    {
        B.BeliefId = FString::Printf(TEXT("blf-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    }
    if (B.Timestamp.IsEmpty())
    {
        B.Timestamp = FDateTime::UtcNow().ToString();
    }

    BeliefStore.Add(B);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][WORLD_MODEL] Registered belief | Agent=%s | Subject=%s | Prop=%s | Val=%s | Conf=%.2f"),
        *B.ObserverAgentId, *B.SubjectEntityId, *B.PropertyName, *B.ClaimedValue, B.Confidence);

    // Detect conflicting belief with peers
    for (const FSarembokAgentBelief& Other : BeliefStore)
    {
        if (Other.ObserverAgentId != B.ObserverAgentId &&
            Other.SubjectEntityId == B.SubjectEntityId &&
            Other.PropertyName == B.PropertyName &&
            Other.ClaimedValue != B.ClaimedValue)
        {
            FSarembokBeliefDisagreement Dis;
            Dis.DisagreementId  = FString::Printf(TEXT("dis-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
            Dis.SubjectEntityId = B.SubjectEntityId;
            Dis.PropertyName    = B.PropertyName;
            Dis.AgentABelief    = Other.ClaimedValue;
            Dis.AgentBBelief    = B.ClaimedValue;
            Dis.bResolved       = false;

            DisagreementStore.Add(Dis.DisagreementId, Dis);
            UE_LOG(LogTemp, Warning, TEXT("[SAREMBOK][WORLD_MODEL] DISAGREEMENT DETECTED | Id=%s | Subject=%s | A=%s | B=%s"),
                *Dis.DisagreementId, *Dis.SubjectEntityId, *Dis.AgentABelief, *Dis.AgentBBelief);
        }
    }
}

TArray<FSarembokBeliefDisagreement> USarembokWorldModel::DetectDisagreements() const
{
    TArray<FSarembokBeliefDisagreement> Result;
    DisagreementStore.GenerateValueArray(Result);
    return Result;
}

bool USarembokWorldModel::ResolveDisagreement(const FString& DisagreementId, const FString& ConsensusValue)
{
    if (FSarembokBeliefDisagreement* Found = DisagreementStore.Find(DisagreementId))
    {
        Found->bResolved      = true;
        Found->ResolvedValue  = ConsensusValue;

        UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][WORLD_MODEL] Disagreement resolved | Id=%s | ConsensusVal=%s"),
            *DisagreementId, *ConsensusValue);
        return true;
    }
    return false;
}
