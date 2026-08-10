// ============================================================
// SarembokWorldModel.h
// Persistent World Model & Epistemic Belief Tracking — Sarembok VE 3.0
// ============================================================
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokWorldModel.generated.h"

UENUM(BlueprintType)
enum class EWorldEntityType : uint8
{
    Human       UMETA(DisplayName="Human"),
    Agent       UMETA(DisplayName="Agent"),
    Object      UMETA(DisplayName="Object"),
    Location    UMETA(DisplayName="Location"),
    Environment UMETA(DisplayName="Environment")
};

USTRUCT(BlueprintType)
struct FSarembokWorldEntity
{
    GENERATED_BODY()

    UPROPERTY() FString          EntityId;
    UPROPERTY() FString          Name;
    UPROPERTY() EWorldEntityType EntityType;
    UPROPERTY() FVector          Location;
    UPROPERTY() FString          StateJson;
    UPROPERTY() FString          LastUpdatedByAgent;
    UPROPERTY() FString          Timestamp;
};

USTRUCT(BlueprintType)
struct FSarembokAgentBelief
{
    GENERATED_BODY()

    UPROPERTY() FString BeliefId;
    UPROPERTY() FString ObserverAgentId;
    UPROPERTY() FString SubjectEntityId;
    UPROPERTY() FString PropertyName;
    UPROPERTY() FString ClaimedValue;
    UPROPERTY() float   Confidence;
    UPROPERTY() FString SourceTraceId;
    UPROPERTY() FString Timestamp;
};

USTRUCT(BlueprintType)
struct FSarembokBeliefDisagreement
{
    GENERATED_BODY()

    UPROPERTY() FString DisagreementId;
    UPROPERTY() FString SubjectEntityId;
    UPROPERTY() FString PropertyName;
    UPROPERTY() FString AgentABelief;
    UPROPERTY() FString AgentBBelief;
    UPROPERTY() bool    bResolved;
    UPROPERTY() FString ResolvedValue;
};

UCLASS()
class SAREMBOKMEMORY_API USarembokWorldModel : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|WorldModel")
    void UpsertEntity(const FSarembokWorldEntity& Entity);

    UFUNCTION(BlueprintCallable, Category="Sarembok|WorldModel")
    FSarembokWorldEntity GetEntity(const FString& EntityId) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|WorldModel")
    TArray<FSarembokWorldEntity> GetAllEntities() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|WorldModel")
    void RegisterBelief(const FSarembokAgentBelief& Belief);

    UFUNCTION(BlueprintCallable, Category="Sarembok|WorldModel")
    TArray<FSarembokBeliefDisagreement> DetectDisagreements() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|WorldModel")
    bool ResolveDisagreement(const FString& DisagreementId, const FString& ConsensusValue);

private:
    TMap<FString, FSarembokWorldEntity> Entities;
    TArray<FSarembokAgentBelief> BeliefStore;
    TMap<FString, FSarembokBeliefDisagreement> DisagreementStore;
};
