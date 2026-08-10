// ============================================================
// SarembokEmbodiedActionPipeline.cpp
// Embodied Action Completeness Subsystem — Sarembok VE 3.0
// ============================================================
#include "SarembokEmbodiedActionPipeline.h"
#include "Misc/Guid.h"

void USarembokEmbodiedActionPipeline::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][EMBODIED_ACTION] Action Pipeline ONLINE | v3.0 | 14 Actions Supported"));
}

FSarembokEmbodiedAction USarembokEmbodiedActionPipeline::CreateAction(
    const FString& AgentId, EEmbodiedActionType ActionType,
    const FString& Target, float RiskScore, float Confidence)
{
    FSarembokEmbodiedAction Act;
    Act.ActionId             = FString::Printf(TEXT("act-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    Act.AgentId              = AgentId;
    Act.ActionType           = ActionType;
    Act.TargetEntityOrTopic  = Target;
    Act.TargetLocation       = FVector::ZeroVector;
    Act.RiskScore            = RiskScore;
    Act.Confidence           = Confidence;
    Act.GovernanceAuditToken = FString::Printf(TEXT("gov-%s-%s"), *AgentId.Left(6), *Act.ActionId.Left(6));
    Act.bAuthorized          = (RiskScore <= 0.65f && Confidence >= 0.65f);
    Act.bExecuted            = false;

    Actions.Add(Act.ActionId, Act);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][EMBODIED_ACTION] Created action | ActId=%s | Agent=%s | Type=%d | Tgt=%s | Auth=%s"),
        *Act.ActionId, *AgentId, (int32)ActionType, *Target, Act.bAuthorized ? TEXT("true") : TEXT("false"));

    return Act;
}

bool USarembokEmbodiedActionPipeline::ExecuteAction(const FString& ActionId)
{
    if (FSarembokEmbodiedAction* Found = Actions.Find(ActionId))
    {
        if (!Found->bAuthorized)
        {
            UE_LOG(LogTemp, Warning, TEXT("[SAREMBOK][EMBODIED_ACTION] EXECUTION BLOCKED BY GOVERNANCE | ActId=%s"), *ActionId);
            return false;
        }

        Found->bExecuted = true;
        UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][EMBODIED_ACTION] EXECUTED ACTION | ActId=%s | Agent=%s | Type=%d"),
            *ActionId, *Found->AgentId, (int32)Found->ActionType);
        return true;
    }
    return false;
}

FSarembokEmbodiedAction USarembokEmbodiedActionPipeline::GetAction(const FString& ActionId) const
{
    const FSarembokEmbodiedAction* Found = Actions.Find(ActionId);
    return Found ? *Found : FSarembokEmbodiedAction{};
}
