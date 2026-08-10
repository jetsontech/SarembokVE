// ============================================================
// SarembokRuntimeOrchestrator.h
// Unified Cognitive Cycle Orchestrator — Sarembok_VE v2.0
// ============================================================
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokRuntimeOrchestrator.generated.h"

UENUM(BlueprintType)
enum class ECognitiveCycleStage : uint8
{
    Idle            UMETA(DisplayName="Idle"),
    Vision          UMETA(DisplayName="Vision"),
    MemoryRetrieval UMETA(DisplayName="MemoryRetrieval"),
    ContextBuilding UMETA(DisplayName="ContextBuilding"),
    Reasoning       UMETA(DisplayName="Reasoning"),
    GoalSelection   UMETA(DisplayName="GoalSelection"),
    PolicyEvaluation UMETA(DisplayName="PolicyEvaluation"),
    ActionDispatch  UMETA(DisplayName="ActionDispatch"),
    Evaluation      UMETA(DisplayName="Evaluation"),
    Learning        UMETA(DisplayName="Learning"),
    Persist         UMETA(DisplayName="Persist")
};

USTRUCT(BlueprintType)
struct FSarembokCognitiveCycleState
{
    GENERATED_BODY()

    UPROPERTY() FString           AgentId;
    UPROPERTY() ECognitiveCycleStage Stage;
    UPROPERTY() float             CycleStartTimeMs;
    UPROPERTY() float             LastCycleDurationMs;
    UPROPERTY() int32             TotalCyclesCompleted;
    UPROPERTY() bool              bCycleActive;
};

UCLASS()
class SAREMBOKCORE_API USarembokRuntimeOrchestrator : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    void StartCognitiveCycle(const FString& AgentId);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    void StopCognitiveCycle(const FString& AgentId);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    FSarembokCognitiveCycleState GetCycleState(const FString& AgentId) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    TArray<FString> GetActiveAgentIds() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Platform")
    void AdvanceCycle(const FString& AgentId);

private:
    TMap<FString, FSarembokCognitiveCycleState> ActiveCycles;

    void TransitionStage(FSarembokCognitiveCycleState& State, ECognitiveCycleStage Next);
    FString StageToString(ECognitiveCycleStage Stage) const;
};
