#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Containers/Ticker.h"
#include "SarembokReasoningProvider.h"
#include "SarembokAgentManager.generated.h"

UENUM(BlueprintType)
enum class ESarembokAgentState : uint8
{
    Idle            UMETA(DisplayName = "Idle"),
    Perceive        UMETA(DisplayName = "Perceive"),
    Interpret       UMETA(DisplayName = "Interpret"),
    Recall          UMETA(DisplayName = "Recall"),
    FormGoal        UMETA(DisplayName = "FormGoal"),
    Plan            UMETA(DisplayName = "Plan"),
    SelectAction    UMETA(DisplayName = "SelectAction"),
    PolicyCheck     UMETA(DisplayName = "PolicyCheck"),
    Execute         UMETA(DisplayName = "Execute"),
    ObserveResult   UMETA(DisplayName = "ObserveResult"),
    Evaluate        UMETA(DisplayName = "Evaluate"),
    Learn           UMETA(DisplayName = "Learn"),
    Persist         UMETA(DisplayName = "Persist"),
    Replan          UMETA(DisplayName = "Replan"),
    Completed       UMETA(DisplayName = "Completed"),
    Failed          UMETA(DisplayName = "Failed"),
    Shutdown        UMETA(DisplayName = "Shutdown")
};

USTRUCT(BlueprintType)
struct FSarembokTask
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString TaskId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString Intent;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString Payload;
};

UCLASS()
class SAREMBOKAGENT_API USarembokAgentManager : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok Agent")
    FString SubmitTask(const FSarembokTask& Task);

    /**
     * v1.3 goal-oriented autonomous perception-reasoning-action-replanning cycle.
     * Returns true if an action was generated and dispatched.
     */
    UFUNCTION(BlueprintCallable, Category="Sarembok Agent")
    bool RunAutonomousLoop(FString& OutGeneratedCommand);

    UFUNCTION(BlueprintPure, Category="Sarembok Agent")
    FString GetAgentState() const;

    UFUNCTION(BlueprintPure, Category="Sarembok Agent")
    FSarembokTask GetActiveTask() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok Agent")
    void CancelCurrentTask();

    // ---- v1.3 Goal Management ----

    UFUNCTION(BlueprintCallable, Category="Sarembok Agent")
    void PushGoal(const FSarembokGoal& Goal);

    UFUNCTION(BlueprintCallable, Category="Sarembok Agent")
    bool PopGoal(FSarembokGoal& OutGoal);

    UFUNCTION(BlueprintPure, Category="Sarembok Agent")
    FSarembokGoal GetActiveGoal() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok Agent")
    bool CompleteActiveGoal();

    UFUNCTION(BlueprintCallable, Category="Sarembok Agent")
    bool FailActiveGoal(const FString& Reason);

    UFUNCTION(BlueprintPure, Category="Sarembok Agent")
    int32 GetGoalCount() const;

    // ---- v1.3 Reasoner & Replanning Controls ----

    void SetReasoningProvider(TUniquePtr<ISarembokReasoningProvider> NewProvider);

    UFUNCTION(BlueprintCallable, Category="Sarembok Agent")
    void SetLLMMode(bool bEnableLLM);

    UFUNCTION(BlueprintPure, Category="Sarembok Agent")
    FString GetActiveProviderName() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok Agent")
    void SetSimulateActionFailure(bool bSimulate);

private:

    bool ProcessAutonomousTick(float DeltaTime);

    ESarembokAgentState CurrentState;
    FSarembokTask ActiveTask;
    int32 LoopCounter = 0;
    int32 IdleCycleCounter = 0;

    FTSTicker::FDelegateHandle TickerHandle;

    TUniquePtr<ISarembokReasoningProvider> ReasoningProvider;

    // v1.3 Goal Stack
    TArray<FSarembokGoal> GoalStack;

    // v1.3 Failure recovery testing flag
    bool bSimulateFailure = false;

    void TransitionState(ESarembokAgentState NewState, const FString& TraceId);
    static FString StateToString(ESarembokAgentState State);
};
