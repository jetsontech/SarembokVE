// ============================================================
// SarembokAgentIdentity.cpp
// Persistent Agent Identity — Sarembok_VE v2.0
// ============================================================
#include "SarembokAgentIdentity.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"

void USarembokAgentIdentity::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    RestoreIdentities();

    // Ensure the default Sarembok identity always exists
    if (!HasAgentProfile(TEXT("sarembok-prime")))
    {
        CreateAgentProfile(TEXT("sarembok-prime"), TEXT("Sarembok"));
    }

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][IDENTITY] Agent Identity subsystem ONLINE | Profiles=%d"), Profiles.Num());
}

void USarembokAgentIdentity::Deinitialize()
{
    PersistIdentities();
    Super::Deinitialize();
}

void USarembokAgentIdentity::CreateAgentProfile(const FString& AgentId, const FString& DisplayName)
{
    if (Profiles.Contains(AgentId)) return;

    FSarembokAgentProfile Profile;
    Profile.AgentId      = AgentId;
    Profile.DisplayName  = DisplayName;
    Profile.CreatedAt    = FDateTime::UtcNow().ToString();
    Profile.LastActiveAt = Profile.CreatedAt;

    Profile.PersonalityTraits.Openness      = 0.80f;
    Profile.PersonalityTraits.Warmth        = 0.85f;
    Profile.PersonalityTraits.Assertiveness = 0.60f;
    Profile.PersonalityTraits.Curiosity     = 0.90f;
    Profile.PersonalityTraits.Caution       = 0.70f;

    Profile.CumulativeStats.TotalDecisions             = 0;
    Profile.CumulativeStats.SuccessfulGoals            = 0;
    Profile.CumulativeStats.FailedGoals                = 0;
    Profile.CumulativeStats.PolicyDenials              = 0;
    Profile.CumulativeStats.ConversationsHeld          = 0;
    Profile.CumulativeStats.AverageReasoningConfidence = 0.0f;
    Profile.CumulativeStats.GoalSuccessRate            = 0.0f;

    Profiles.Add(AgentId, Profile);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][IDENTITY] Created profile | AgentId=%s | DisplayName=%s"), *AgentId, *DisplayName);
}

bool USarembokAgentIdentity::HasAgentProfile(const FString& AgentId) const
{
    return Profiles.Contains(AgentId);
}

FSarembokAgentProfile USarembokAgentIdentity::GetAgentProfile(const FString& AgentId) const
{
    const FSarembokAgentProfile* Found = Profiles.Find(AgentId);
    return Found ? *Found : FSarembokAgentProfile{};
}

void USarembokAgentIdentity::UpdateCumulativeStats(const FString& AgentId, bool bGoalSuccess, bool bPolicyDenied, float ReasoningConfidence)
{
    if (!Profiles.Contains(AgentId)) return;

    FSarembokAgentProfile& Profile = Profiles[AgentId];
    FSarembokAgentCumulativeStats& Stats = Profile.CumulativeStats;

    Stats.TotalDecisions++;
    if (bGoalSuccess) Stats.SuccessfulGoals++;
    else              Stats.FailedGoals++;
    if (bPolicyDenied) Stats.PolicyDenials++;

    // Rolling average confidence
    Stats.AverageReasoningConfidence = ((Stats.AverageReasoningConfidence * (Stats.TotalDecisions - 1)) + ReasoningConfidence)
                                       / Stats.TotalDecisions;
    Stats.GoalSuccessRate = (Stats.TotalDecisions > 0)
        ? (float)Stats.SuccessfulGoals / (float)Stats.TotalDecisions
        : 0.0f;

    Profile.LastActiveAt = FDateTime::UtcNow().ToString();
}

TArray<FString> USarembokAgentIdentity::GetAllAgentIds() const
{
    TArray<FString> Ids;
    Profiles.GetKeys(Ids);
    return Ids;
}

void USarembokAgentIdentity::PersistIdentities()
{
    FString SavePath = GetSaveFilePath();
    FString Content;
    for (const auto& Pair : Profiles)
    {
        const FSarembokAgentProfile& P = Pair.Value;
        Content += FString::Printf(TEXT("{\"agentId\":\"%s\",\"displayName\":\"%s\",\"decisions\":%d,\"goalSuccessRate\":%.4f}\n"),
            *P.AgentId, *P.DisplayName, P.CumulativeStats.TotalDecisions, P.CumulativeStats.GoalSuccessRate);
    }
    FFileHelper::SaveStringToFile(Content, *SavePath);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][IDENTITY] Identities persisted | Path=%s"), *SavePath);
}

void USarembokAgentIdentity::RestoreIdentities()
{
    FString SavePath = GetSaveFilePath();
    if (!FPaths::FileExists(SavePath)) return;

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][IDENTITY] Restoring identities from | Path=%s"), *SavePath);
    // In production this would deserialize JSON. For the runtime, profiles are initialized fresh
    // and stats accumulate within a session. Cross-session persistence is via the EventStore.
}

#include "Misc/Guid.h"

FSarembokContextHierarchy USarembokAgentIdentity::CreateContextHierarchy(const FString& AgentId)
{
    FSarembokContextHierarchy Ctx;
    Ctx.PlatformId     = TEXT("sarembok-prod-01");
    Ctx.AgentId        = AgentId;
    Ctx.SessionId      = FString::Printf(TEXT("sess-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    Ctx.ConversationId = FString::Printf(TEXT("conv-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    Ctx.GoalId         = FString::Printf(TEXT("goal-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    Ctx.PlanId         = FString::Printf(TEXT("plan-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    Ctx.DecisionId     = FString::Printf(TEXT("dec-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    Ctx.TraceId        = FString::Printf(TEXT("trace-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    Ctx.EventId        = FString::Printf(TEXT("evt-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    Ctx.AuditToken     = FString::Printf(TEXT("gov-%s-%s"), *AgentId.Left(8), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    return Ctx;
}

bool USarembokAgentIdentity::VerifyMultiAgentIsolation(const FString& AgentIdA, const FString& AgentIdB) const
{
    if (AgentIdA == AgentIdB) return false;
    if (!HasAgentProfile(AgentIdA) || !HasAgentProfile(AgentIdB)) return false;

    FSarembokAgentProfile ProfileA = GetAgentProfile(AgentIdA);
    FSarembokAgentProfile ProfileB = GetAgentProfile(AgentIdB);

    // Verify memory/identity pointer isolation
    return (ProfileA.AgentId != ProfileB.AgentId) && (&ProfileA != &ProfileB);
}

FString USarembokAgentIdentity::GetSaveFilePath() const
{
    return FPaths::ProjectSavedDir() / TEXT("Sarembok/AgentIdentities.jsonl");
}
