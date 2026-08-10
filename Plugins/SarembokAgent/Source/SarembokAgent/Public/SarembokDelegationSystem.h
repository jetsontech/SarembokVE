// ============================================================
// SarembokDelegationSystem.h
// Event-Driven Task Delegation System — Sarembok_VE v2.1
// ============================================================
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokDelegationSystem.generated.h"

UENUM(BlueprintType)
enum class EDelegationStatus : uint8
{
    Created     UMETA(DisplayName="Created"),
    Authorized  UMETA(DisplayName="Authorized"),
    Accepted    UMETA(DisplayName="Accepted"),
    Executing   UMETA(DisplayName="Executing"),
    Completed   UMETA(DisplayName="Completed"),
    Failed      UMETA(DisplayName="Failed"),
    Reassigned  UMETA(DisplayName="Reassigned"),
    Cancelled   UMETA(DisplayName="Cancelled")
};

USTRUCT(BlueprintType)
struct FSarembokDelegationRecord
{
    GENERATED_BODY()

    UPROPERTY() FString           DelegationId;
    UPROPERTY() FString           SourceAgentId;
    UPROPERTY() FString           TargetAgentId;
    UPROPERTY() FString           GoalId;
    UPROPERTY() FString           RequiredCapability;
    UPROPERTY() EDelegationStatus Status;
    UPROPERTY() FString           ResultData;
    UPROPERTY() int32             RetryCount;
    UPROPERTY() FString           Timestamp;
};

USTRUCT(BlueprintType)
struct FSarembokMultiAgentPlanStep
{
    GENERATED_BODY()

    UPROPERTY() FString           StepId;
    UPROPERTY() FString           GoalId;
    UPROPERTY() FString           AssignedAgentId;
    UPROPERTY() FString           RequiredCapability;
    UPROPERTY() TArray<FString>    Dependencies;
    UPROPERTY() FString           Status;
    UPROPERTY() FString           ExpectedOutcome;
    UPROPERTY() int32             MaxRetries;
};

UCLASS()
class SAREMBOKAGENT_API USarembokDelegationSystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Delegation")
    FSarembokDelegationRecord CreateDelegation(const FString& SourceAgentId, const FString& TargetAgentId, const FString& GoalId, const FString& RequiredCapability);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Delegation")
    bool UpdateDelegationStatus(const FString& DelegationId, EDelegationStatus NewStatus, const FString& ResultData = TEXT(""));

    UFUNCTION(BlueprintCallable, Category="Sarembok|Delegation")
    FSarembokDelegationRecord GetDelegation(const FString& DelegationId) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Delegation")
    bool ReassignDelegation(const FString& DelegationId, const FString& NewTargetAgentId);

private:
    TMap<FString, FSarembokDelegationRecord> Delegations;
};
