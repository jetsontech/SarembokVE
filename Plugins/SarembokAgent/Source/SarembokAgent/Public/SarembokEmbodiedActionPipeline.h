// ============================================================
// SarembokEmbodiedActionPipeline.h
// Embodied Action Completeness Subsystem — Sarembok VE 3.0
// ============================================================
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokEmbodiedActionPipeline.generated.h"

UENUM(BlueprintType)
enum class EEmbodiedActionType : uint8
{
    Speak     UMETA(DisplayName="Speak"),
    Listen    UMETA(DisplayName="Listen"),
    Look      UMETA(DisplayName="Look"),
    Turn      UMETA(DisplayName="Turn"),
    Move      UMETA(DisplayName="Move"),
    Navigate  UMETA(DisplayName="Navigate"),
    Gesture   UMETA(DisplayName="Gesture"),
    Emote     UMETA(DisplayName="Emote"),
    Interact  UMETA(DisplayName="Interact"),
    Remember  UMETA(DisplayName="Remember"),
    Retrieve  UMETA(DisplayName="Retrieve"),
    Query     UMETA(DisplayName="Query"),
    Delegate  UMETA(DisplayName="Delegate"),
    Plan      UMETA(DisplayName="Plan")
};

USTRUCT(BlueprintType)
struct FSarembokEmbodiedAction
{
    GENERATED_BODY()

    UPROPERTY() FString              ActionId;
    UPROPERTY() FString              AgentId;
    UPROPERTY() EEmbodiedActionType  ActionType;
    UPROPERTY() FString              TargetEntityOrTopic;
    UPROPERTY() FVector              TargetLocation;
    UPROPERTY() FString              PayloadJson;
    UPROPERTY() float                RiskScore;
    UPROPERTY() float                Confidence;
    UPROPERTY() FString              GovernanceAuditToken;
    UPROPERTY() bool                 bAuthorized;
    UPROPERTY() bool                 bExecuted;
};

UCLASS()
class SAREMBOKAGENT_API USarembokEmbodiedActionPipeline : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|EmbodiedAction")
    FSarembokEmbodiedAction CreateAction(const FString& AgentId, EEmbodiedActionType ActionType, const FString& Target, float RiskScore = 0.1f, float Confidence = 0.9f);

    UFUNCTION(BlueprintCallable, Category="Sarembok|EmbodiedAction")
    bool ExecuteAction(const FString& ActionId);

    UFUNCTION(BlueprintCallable, Category="Sarembok|EmbodiedAction")
    FSarembokEmbodiedAction GetAction(const FString& ActionId) const;

private:
    TMap<FString, FSarembokEmbodiedAction> Actions;
};
