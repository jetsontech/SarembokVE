// ============================================================
// SarembokPlatformAPI.h
// External Platform API (JSON-RPC over WebSocket) — Sarembok_VE v2.0
// ============================================================
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokPlatformAPI.generated.h"

USTRUCT(BlueprintType)
struct FSarembokAPIRequest
{
    GENERATED_BODY()

    UPROPERTY() FString Method;
    UPROPERTY() FString RequestId;
    UPROPERTY() TMap<FString, FString> Params;
};

USTRUCT(BlueprintType)
struct FSarembokAPIResponse
{
    GENERATED_BODY()

    UPROPERTY() FString RequestId;
    UPROPERTY() bool    bSuccess;
    UPROPERTY() FString ResultJson;
    UPROPERTY() FString ErrorMessage;
};

UCLASS()
class SAREMBOKBRIDGE_API USarembokPlatformAPI : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    // Core external API methods
    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformAPI")
    FSarembokAPIResponse CreateAgent(const FString& AgentId, const FString& DisplayName);

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformAPI")
    FSarembokAPIResponse QueryAgentState(const FString& AgentId);

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformAPI")
    FSarembokAPIResponse InjectPerception(const FString& AgentId, const FString& PerceptionJson);

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformAPI")
    FSarembokAPIResponse EvaluateDecision(const FString& AgentId, const FString& ActionId, float RiskScore, float Confidence);

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformAPI")
    FSarembokAPIResponse GetCognitiveScorecard(const FString& AgentId);

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformAPI")
    FSarembokAPIResponse QueryWorldModel(const FString& QueryFilter);

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformAPI")
    FSarembokAPIResponse CreateDelegation(const FString& SourceAgentId, const FString& TargetAgentId, const FString& GoalId);

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformAPI")
    FSarembokAPIResponse GetAuditTrail(const FString& AgentId);

    // Dispatch a raw WebSocket JSON-RPC request string
    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformAPI")
    FString DispatchRequest(const FString& RequestJson);

private:
    FSarembokAPIResponse MakeSuccess(const FString& RequestId, const FString& ResultJson) const;
    FSarembokAPIResponse MakeError(const FString& RequestId, const FString& Error) const;
};
