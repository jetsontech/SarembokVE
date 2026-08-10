// ============================================================
// SarembokActionPolicyGate.cpp
// Action Authorization & Policy Safety Gate Implementation
// ============================================================

#include "SarembokActionPolicyGate.h"

void USarembokActionPolicyGate::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    bStrictPolicyMode = true;

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][POLICY_GATE] INITIALIZED | StrictMode=true"));
}

void USarembokActionPolicyGate::Deinitialize()
{
    Super::Deinitialize();
}

EPolicyResult USarembokActionPolicyGate::EvaluateIntentPolicy(const FSarembokIntent& Intent)
{
    if (Intent.ActionType.Equals(TEXT("Speak"), ESearchCase::IgnoreCase) ||
        Intent.ActionType.Equals(TEXT("Emotion"), ESearchCase::IgnoreCase) ||
        Intent.ActionType.Equals(TEXT("Observe"), ESearchCase::IgnoreCase))
    {
        UE_LOG(LogTemp, Display,
            TEXT("[SAREMBOK][POLICY_GATE] POLICY_EVALUATE Action=%s Result=ALLOW Confidence=%.2f"),
            *Intent.ActionType, Intent.Confidence);

        return EPolicyResult::ALLOW;
    }

    if (Intent.ActionType.Equals(TEXT("ExecuteWorldCommand"), ESearchCase::IgnoreCase))
    {
        UE_LOG(LogTemp, Warning,
            TEXT("[SAREMBOK][POLICY_GATE] POLICY_EVALUATE Action=%s Result=CONFIRMATION_REQUIRED Target=%s"),
            *Intent.ActionType, *Intent.Target);

        return EPolicyResult::CONFIRMATION_REQUIRED;
    }

    UE_LOG(LogTemp, Warning,
        TEXT("[SAREMBOK][POLICY_GATE] POLICY_EVALUATE Action=%s Result=DENY Reason=Unauthorized_Action_Type"),
        *Intent.ActionType);

    return EPolicyResult::DENY;
}

void USarembokActionPolicyGate::SetStrictPolicyMode(bool bEnableStrict)
{
    bStrictPolicyMode = bEnableStrict;
}

bool USarembokActionPolicyGate::IsStrictPolicyMode() const
{
    return bStrictPolicyMode;
}
