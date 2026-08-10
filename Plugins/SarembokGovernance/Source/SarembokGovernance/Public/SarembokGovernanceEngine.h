// ============================================================
// SarembokGovernanceEngine.h
// Multi-Factor Cognitive Governance Engine — Sarembok_VE v2.0
// ============================================================
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokGovernanceEngine.generated.h"

UENUM(BlueprintType)
enum class EGovernanceResult : uint8
{
    Allow               UMETA(DisplayName="Allow"),
    Deny                UMETA(DisplayName="Deny"),
    ConfirmationRequired UMETA(DisplayName="ConfirmationRequired")
};

USTRUCT(BlueprintType)
struct FSarembokGovernanceRequest
{
    GENERATED_BODY()

    UPROPERTY() FString UserId;
    UPROPERTY() FString AgentId;
    UPROPERTY() FString GoalId;
    UPROPERTY() FString ActionId;
    UPROPERTY() FString WorldContext;
    UPROPERTY() float   RiskScore;
    UPROPERTY() FString PermissionRequired;
    UPROPERTY() float   ReasoningConfidence;
};

USTRUCT(BlueprintType)
struct FSarembokGovernanceDecision
{
    GENERATED_BODY()

    UPROPERTY() EGovernanceResult Result;
    UPROPERTY() FString           Reason;
    UPROPERTY() FString           AuditToken;
    UPROPERTY() float             EvaluatedRiskScore;
    UPROPERTY() FString           Timestamp;
};

UENUM(BlueprintType)
enum class EAgentRoleType : uint8
{
    Observer       UMETA(DisplayName="Observer"),
    Conversational UMETA(DisplayName="Conversational"),
    Navigator      UMETA(DisplayName="Navigator"),
    Researcher     UMETA(DisplayName="Researcher"),
    Admin          UMETA(DisplayName="Admin")
};

USTRUCT(BlueprintType)
struct FSarembokAgentRole
{
    GENERATED_BODY()

    UPROPERTY() EAgentRoleType RoleType;
    UPROPERTY() FString        RoleName;
    UPROPERTY() TArray<FString> AllowedCapabilities;
};

USTRUCT(BlueprintType)
struct FSarembokAgentQuota
{
    GENERATED_BODY()

    UPROPERTY() int32 MaxConcurrentTasks;
    UPROPERTY() int32 MaxDelegations;
    UPROPERTY() int32 MaxMemoryWrites;
    UPROPERTY() int32 MaxQueriesPerMinute;
    UPROPERTY() int32 MaxWorldActions;
    UPROPERTY() int32 MaxExecutionTimeMs;
};

UCLASS()
class SAREMBOKGOVERNANCE_API USarembokGovernanceEngine : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Governance")
    FSarembokGovernanceDecision EvaluateActionRequest(const FSarembokGovernanceRequest& Request);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Governance")
    void RegisterAgentRole(const FString& AgentId, EAgentRoleType RoleType);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Governance")
    void SetAgentQuota(const FString& AgentId, const FSarembokAgentQuota& Quota);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Governance")
    bool CheckQuotaCompliance(const FString& AgentId, int32 ActionCost = 1) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Governance")
    TArray<FSarembokGovernanceDecision> GetAuditTrail(int32 MaxRecords = 100) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Governance")
    int32 GetTotalDenials() const { return TotalDenials; }

    UFUNCTION(BlueprintCallable, Category="Sarembok|Governance")
    int32 GetTotalAuthorizations() const { return TotalAuthorizations; }

private:
    TArray<FSarembokGovernanceDecision> AuditTrail;
    TMap<FString, FSarembokAgentRole> AgentRoles;
    TMap<FString, FSarembokAgentQuota> AgentQuotas;
    int32 TotalDenials        = 0;
    int32 TotalAuthorizations = 0;

    FString GenerateAuditToken(const FSarembokGovernanceRequest& Request) const;
    bool EvaluateRiskThreshold(float RiskScore, float Confidence) const;
    bool EvaluatePermission(const FString& Permission) const;
};
