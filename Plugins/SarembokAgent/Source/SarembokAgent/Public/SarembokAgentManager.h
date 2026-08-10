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
    Plan            UMETA(DisplayName = "Plan"),
    SelectAction    UMETA(DisplayName = "SelectAction"),
    Execute         UMETA(DisplayName = "Execute"),
    ObserveResult   UMETA(DisplayName = "ObserveResult"),
    Evaluate        UMETA(DisplayName = "Evaluate"),
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
     * v1.2 full perception-reasoning-action cycle.
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

private:

    bool ProcessAutonomousTick(float DeltaTime);

    ESarembokAgentState CurrentState;
    FSarembokTask ActiveTask;
    int32 LoopCounter = 0;
    int32 IdleCycleCounter = 0;

    FTSTicker::FDelegateHandle TickerHandle;

    TUniquePtr<ISarembokReasoningProvider> ReasoningProvider;

    void TransitionState(ESarembokAgentState NewState, const FString& TraceId);
    static FString StateToString(ESarembokAgentState State);
};
