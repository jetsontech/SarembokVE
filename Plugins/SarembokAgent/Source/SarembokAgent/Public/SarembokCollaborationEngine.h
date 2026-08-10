// ============================================================
// SarembokCollaborationEngine.h
// Autonomous Team Bidding & Collaboration Engine — Sarembok VE 3.0
// ============================================================
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokCollaborationEngine.generated.h"

USTRUCT(BlueprintType)
struct FSarembokTaskBid
{
    GENERATED_BODY()

    UPROPERTY() FString BidId;
    UPROPERTY() FString AgentId;
    UPROPERTY() FString TaskId;
    UPROPERTY() float   CapabilityScore;
    UPROPERTY() float   EstimatedDurationMs;
    UPROPERTY() float   Cost;
    UPROPERTY() float   Confidence;
};

USTRUCT(BlueprintType)
struct FSarembokTeamAssembly
{
    GENERATED_BODY()

    UPROPERTY() FString TeamId;
    UPROPERTY() FString GoalId;
    UPROPERTY() FString PlannerAgentId;
    UPROPERTY() FString ResearcherAgentId;
    UPROPERTY() FString ExecutorAgentId;
    UPROPERTY() FString Status;
};

UCLASS()
class SAREMBOKAGENT_API USarembokCollaborationEngine : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Collaboration")
    FSarembokTaskBid SubmitBid(const FString& AgentId, const FString& TaskId, float CapabilityScore, float Cost, float Confidence);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Collaboration")
    FString SelectOptimalWorker(const FString& TaskId);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Collaboration")
    FSarembokTeamAssembly AssembleTeam(const FString& GoalId, const FString& PlannerId, const FString& ResearcherId, const FString& ExecutorId);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Collaboration")
    FSarembokTeamAssembly GetTeam(const FString& TeamId) const;

private:
    TMap<FString, TArray<FSarembokTaskBid>> TaskBids;
    TMap<FString, FSarembokTeamAssembly> Teams;
};
