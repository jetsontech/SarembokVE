// ============================================================
// SarembokAgentIdentity.h
// Persistent Agent Identity — Sarembok_VE v2.0
// ============================================================
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokAgentIdentity.generated.h"

USTRUCT(BlueprintType)
struct FSarembokAgentPersonalityTraits
{
    GENERATED_BODY()

    UPROPERTY() float Openness;
    UPROPERTY() float Warmth;
    UPROPERTY() float Assertiveness;
    UPROPERTY() float Curiosity;
    UPROPERTY() float Caution;
};

USTRUCT(BlueprintType)
struct FSarembokAgentCumulativeStats
{
    GENERATED_BODY()

    UPROPERTY() int32 TotalDecisions;
    UPROPERTY() int32 SuccessfulGoals;
    UPROPERTY() int32 FailedGoals;
    UPROPERTY() int32 PolicyDenials;
    UPROPERTY() int32 ConversationsHeld;
    UPROPERTY() float AverageReasoningConfidence;
    UPROPERTY() float GoalSuccessRate;
};

USTRUCT(BlueprintType)
struct FSarembokAgentProfile
{
    GENERATED_BODY()

    UPROPERTY() FString                       AgentId;
    UPROPERTY() FString                       DisplayName;
    UPROPERTY() FString                       CreatedAt;
    UPROPERTY() FString                       LastActiveAt;
    UPROPERTY() FSarembokAgentPersonalityTraits PersonalityTraits;
    UPROPERTY() FSarembokAgentCumulativeStats  CumulativeStats;
    UPROPERTY() TMap<FString, FString>         PersistentConfiguration;
};

USTRUCT(BlueprintType)
struct FSarembokContextHierarchy
{
    GENERATED_BODY()

    UPROPERTY() FString PlatformId;
    UPROPERTY() FString AgentId;
    UPROPERTY() FString SessionId;
    UPROPERTY() FString ConversationId;
    UPROPERTY() FString GoalId;
    UPROPERTY() FString PlanId;
    UPROPERTY() FString DecisionId;
    UPROPERTY() FString TraceId;
    UPROPERTY() FString EventId;
    UPROPERTY() FString AuditToken;
};

UCLASS()
class SAREMBOKCORE_API USarembokAgentIdentity : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    void CreateAgentProfile(const FString& AgentId, const FString& DisplayName);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    bool HasAgentProfile(const FString& AgentId) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    FSarembokAgentProfile GetAgentProfile(const FString& AgentId) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    void UpdateCumulativeStats(const FString& AgentId, bool bGoalSuccess, bool bPolicyDenied, float ReasoningConfidence);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    TArray<FString> GetAllAgentIds() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    FSarembokContextHierarchy CreateContextHierarchy(const FString& AgentId);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    bool VerifyMultiAgentIsolation(const FString& AgentIdA, const FString& AgentIdB) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    void PersistIdentities();

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    void RestoreIdentities();

private:
    TMap<FString, FSarembokAgentProfile> Profiles;
    FString GetSaveFilePath() const;
};
