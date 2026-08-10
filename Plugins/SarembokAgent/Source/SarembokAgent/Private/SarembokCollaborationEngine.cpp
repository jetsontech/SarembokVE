// ============================================================
// SarembokCollaborationEngine.cpp
// Autonomous Team Bidding & Collaboration Engine — Sarembok VE 3.0
// ============================================================
#include "SarembokCollaborationEngine.h"
#include "Misc/Guid.h"

void USarembokCollaborationEngine::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][COLLABORATION] SarembokCollaborationEngine Subsystem ONLINE | v3.0"));
}

FSarembokTaskBid USarembokCollaborationEngine::SubmitBid(
    const FString& AgentId, const FString& TaskId,
    float CapabilityScore, float Cost, float Confidence)
{
    FSarembokTaskBid Bid;
    Bid.BidId               = FString::Printf(TEXT("bid-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    Bid.AgentId             = AgentId;
    Bid.TaskId              = TaskId;
    Bid.CapabilityScore     = CapabilityScore;
    Bid.EstimatedDurationMs = 1500.0f;
    Bid.Cost                = Cost;
    Bid.Confidence          = Confidence;

    TaskBids.FindOrAdd(TaskId).Add(Bid);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][COLLABORATION] Submitted bid | BidId=%s | Agent=%s | Task=%s | Cap=%.2f | Conf=%.2f"),
        *Bid.BidId, *AgentId, *TaskId, CapabilityScore, Confidence);

    return Bid;
}

FString USarembokCollaborationEngine::SelectOptimalWorker(const FString& TaskId)
{
    if (const TArray<FSarembokTaskBid>* Bids = TaskBids.Find(TaskId))
    {
        float BestScore = -1.0f;
        FString BestAgentId = TEXT("");

        for (const FSarembokTaskBid& B : *Bids)
        {
            float Composite = (B.CapabilityScore * 0.5f) + (B.Confidence * 0.5f) - (B.Cost * 0.1f);
            if (Composite > BestScore)
            {
                BestScore = Composite;
                BestAgentId = B.AgentId;
            }
        }

        UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][COLLABORATION] Selected optimal worker for task '%s' -> '%s' (Score=%.2f)"),
            *TaskId, *BestAgentId, BestScore);

        return BestAgentId;
    }
    return TEXT("");
}

FSarembokTeamAssembly USarembokCollaborationEngine::AssembleTeam(
    const FString& GoalId, const FString& PlannerId,
    const FString& ResearcherId, const FString& ExecutorId)
{
    FSarembokTeamAssembly Team;
    Team.TeamId            = FString::Printf(TEXT("team-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Short));
    Team.GoalId            = GoalId;
    Team.PlannerAgentId    = PlannerId;
    Team.ResearcherAgentId = ResearcherId;
    Team.ExecutorAgentId   = ExecutorId;
    Team.Status            = TEXT("ACTIVE");

    Teams.Add(Team.TeamId, Team);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][COLLABORATION] Team assembled | TeamId=%s | Goal=%s | Planner=%s | Research=%s | Exec=%s"),
        *Team.TeamId, *GoalId, *PlannerId, *ResearcherId, *ExecutorId);

    return Team;
}

FSarembokTeamAssembly USarembokCollaborationEngine::GetTeam(const FString& TeamId) const
{
    const FSarembokTeamAssembly* Found = Teams.Find(TeamId);
    return Found ? *Found : FSarembokTeamAssembly{};
}
