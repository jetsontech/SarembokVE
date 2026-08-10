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

UCLASS()
class SAREMBOKGOVERNANCE_API USarembokGovernanceEngine : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Governance")
    FSarembokGovernanceDecision EvaluateActionRequest(const FSarembokGovernanceRequest& Request);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Governance")
    TArray<FSarembokGovernanceDecision> GetAuditTrail(int32 MaxRecords = 100) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Governance")
    int32 GetTotalDenials() const { return TotalDenials; }

    UFUNCTION(BlueprintCallable, Category="Sarembok|Governance")
    int32 GetTotalAuthorizations() const { return TotalAuthorizations; }

private:
    TArray<FSarembokGovernanceDecision> AuditTrail;
    int32 TotalDenials        = 0;
    int32 TotalAuthorizations = 0;

    FString GenerateAuditToken(const FSarembokGovernanceRequest& Request) const;
    bool EvaluateRiskThreshold(float RiskScore, float Confidence) const;
    bool EvaluatePermission(const FString& Permission) const;
};
