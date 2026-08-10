// ============================================================
// SarembokGovernanceEngine.cpp
// Multi-Factor Cognitive Governance Engine — Sarembok_VE v2.0
// ============================================================
#include "SarembokGovernanceEngine.h"
#include "Misc/Guid.h"

void USarembokGovernanceEngine::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][GOVERNANCE] Engine initialized | RiskThreshold=0.75 | ConfidenceFloor=0.65"));
}

FSarembokGovernanceDecision USarembokGovernanceEngine::EvaluateActionRequest(const FSarembokGovernanceRequest& Request)
{
    FSarembokGovernanceDecision Decision;
    Decision.EvaluatedRiskScore = Request.RiskScore;
    Decision.AuditToken         = GenerateAuditToken(Request);
    Decision.Timestamp          = FDateTime::UtcNow().ToString();

    // Tier 1: confidence floor — low confidence cannot authorize high-risk actions
    if (Request.ReasoningConfidence < 0.65f && Request.RiskScore > 0.4f)
    {
        Decision.Result = EGovernanceResult::Deny;
        Decision.Reason = FString::Printf(
            TEXT("Insufficient confidence (%.2f) for elevated risk action '%s'"),
            Request.ReasoningConfidence, *Request.ActionId);
        TotalDenials++;
        AuditTrail.Add(Decision);
        UE_LOG(LogTemp, Warning, TEXT("[SAREMBOK][GOVERNANCE] DENY | %s | Token=%s"), *Decision.Reason, *Decision.AuditToken);
        return Decision;
    }

    // Tier 2: hard risk ceiling
    if (Request.RiskScore > 0.90f)
    {
        Decision.Result = EGovernanceResult::Deny;
        Decision.Reason = FString::Printf(TEXT("RiskScore=%.2f exceeds hard ceiling (0.90) for action '%s'"), Request.RiskScore, *Request.ActionId);
        TotalDenials++;
        AuditTrail.Add(Decision);
        UE_LOG(LogTemp, Warning, TEXT("[SAREMBOK][GOVERNANCE] DENY | %s | Token=%s"), *Decision.Reason, *Decision.AuditToken);
        return Decision;
    }

    // Tier 3: elevated risk requires explicit confirmation
    if (Request.RiskScore > 0.65f)
    {
        Decision.Result = EGovernanceResult::ConfirmationRequired;
        Decision.Reason = FString::Printf(TEXT("RiskScore=%.2f requires confirmation for action '%s'"), Request.RiskScore, *Request.ActionId);
        AuditTrail.Add(Decision);
        UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][GOVERNANCE] CONFIRM_REQUIRED | %s | Token=%s"), *Decision.Reason, *Decision.AuditToken);
        return Decision;
    }

    // Tier 4: permission check
    if (!EvaluatePermission(Request.PermissionRequired))
    {
        Decision.Result = EGovernanceResult::Deny;
        Decision.Reason = FString::Printf(TEXT("Permission '%s' not granted for action '%s'"), *Request.PermissionRequired, *Request.ActionId);
        TotalDenials++;
        AuditTrail.Add(Decision);
        UE_LOG(LogTemp, Warning, TEXT("[SAREMBOK][GOVERNANCE] DENY | %s | Token=%s"), *Decision.Reason, *Decision.AuditToken);
        return Decision;
    }

    // ALLOW
    Decision.Result = EGovernanceResult::Allow;
    Decision.Reason = TEXT("All governance tiers passed");
    TotalAuthorizations++;
    AuditTrail.Add(Decision);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][GOVERNANCE] ALLOW | Action=%s | Risk=%.2f | Confidence=%.2f | Token=%s"),
        *Request.ActionId, Request.RiskScore, Request.ReasoningConfidence, *Decision.AuditToken);
    return Decision;
}

TArray<FSarembokGovernanceDecision> USarembokGovernanceEngine::GetAuditTrail(int32 MaxRecords) const
{
    int32 StartIdx = FMath::Max(0, AuditTrail.Num() - MaxRecords);
    return TArray<FSarembokGovernanceDecision>(AuditTrail.GetData() + StartIdx, AuditTrail.Num() - StartIdx);
}

FString USarembokGovernanceEngine::GenerateAuditToken(const FSarembokGovernanceRequest& Request) const
{
    return FString::Printf(TEXT("gov-%s-%s-%s"),
        *Request.AgentId.Left(8),
        *Request.ActionId.Left(12),
        *FGuid::NewGuid().ToString(EGuidFormats::Short));
}

bool USarembokGovernanceEngine::EvaluateRiskThreshold(float RiskScore, float Confidence) const
{
    return (RiskScore <= 0.65f) || (Confidence >= 0.80f && RiskScore <= 0.90f);
}

bool USarembokGovernanceEngine::EvaluatePermission(const FString& Permission) const
{
    // All agent.* permissions are granted in the base governance profile.
    // Production deployments would check against a user-scoped permission store.
    return Permission.StartsWith(TEXT("agent.")) || Permission.IsEmpty();
}
