// ============================================================
// SarembokAgentBus.h
// Inter-Agent Event Bus & Governed Messaging Envelope — Sarembok_VE v2.1
// ============================================================
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokAgentBus.generated.h"

UENUM(BlueprintType)
enum class EAgentMessageType : uint8
{
    Request      UMETA(DisplayName="Request"),
    Response     UMETA(DisplayName="Response"),
    Delegate     UMETA(DisplayName="Delegate"),
    Result       UMETA(DisplayName="Result"),
    Inform       UMETA(DisplayName="Inform"),
    Perception   UMETA(DisplayName="Perception"),
    PlanProposal UMETA(DisplayName="PlanProposal"),
    PlanUpdate   UMETA(DisplayName="PlanUpdate"),
    Cancel       UMETA(DisplayName="Cancel"),
    Heartbeat    UMETA(DisplayName="Heartbeat")
};

USTRUCT(BlueprintType)
struct FAgentMessage
{
    GENERATED_BODY()

    UPROPERTY() FString           MessageId;
    UPROPERTY() FString           TraceId;
    UPROPERTY() FString           SourceAgentId;
    UPROPERTY() FString           TargetAgentId;
    UPROPERTY() FString           ConversationId;
    UPROPERTY() EAgentMessageType MessageType;
    UPROPERTY() int32             Priority;
    UPROPERTY() FString           Timestamp;
    UPROPERTY() FString           PayloadJson;
    UPROPERTY() FString           RequiredCapability;
    UPROPERTY() FString           AuthorizationContext;
    UPROPERTY() float             TTLSeconds;
    UPROPERTY() bool              bCancelled;
};

UCLASS()
class SAREMBOKCORE_API USarembokAgentBus : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|AgentBus")
    FString SendMessage(const FAgentMessage& Message);

    UFUNCTION(BlueprintCallable, Category="Sarembok|AgentBus")
    void SubscribeTopic(const FString& AgentId, const FString& Topic);

    UFUNCTION(BlueprintCallable, Category="Sarembok|AgentBus")
    TArray<FAgentMessage> GetPendingMessages(const FString& AgentId);

    UFUNCTION(BlueprintCallable, Category="Sarembok|AgentBus")
    bool CancelMessage(const FString& MessageId);

    UFUNCTION(BlueprintCallable, Category="Sarembok|AgentBus")
    int32 GetTotalMessagesRouted() const { return TotalMessagesRouted; }

private:
    TMap<FString, TArray<FAgentMessage>> OutboxPerAgent;
    TMap<FString, FAgentMessage> MessageStore;
    int32 TotalMessagesRouted = 0;
};
