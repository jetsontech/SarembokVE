#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokAgentManager.h"
#include "SarembokReasoningProvider.h"
#include "SarembokDemoStimulusActor.h"
#include "SarembokDemoController.generated.h"

UCLASS(Blueprintable)
class SAREMBOKAGENT_API ASarembokDemoController : public AActor
{
    GENERATED_BODY()

public:
    ASarembokDemoController();

protected:
    virtual void BeginPlay() override;

public:
    /**
     * Start the complete v1.3 goal-oriented autonomous demo flow.
     */
    UFUNCTION(BlueprintCallable, Category = "Sarembok|Demo")
    void StartAutonomousDemo();

    /**
     * Create and push the deterministic demonstration goal:
     * Id: demo.observe.respond
     * Description: "Observe the environment and respond when a new actor appears."
     * Priority: 80
     * TargetState: "environment_observed_and_response_completed"
     */
    UFUNCTION(BlueprintCallable, Category = "Sarembok|Demo")
    FSarembokGoal CreateDemoGoal();

    /**
     * Clear all current goals from the agent goal stack.
     */
    UFUNCTION(BlueprintCallable, Category = "Sarembok|Demo")
    void ClearDemoGoals();

    /**
     * Get the active goal on the stack.
     */
    UFUNCTION(BlueprintPure, Category = "Sarembok|Demo")
    FSarembokGoal GetCurrentGoal() const;

    /**
     * Get the active intent.
     */
    UFUNCTION(BlueprintPure, Category = "Sarembok|Demo")
    FSarembokIntent GetCurrentIntent() const;

    /**
     * Get confidence of active intent.
     */
    UFUNCTION(BlueprintPure, Category = "Sarembok|Demo")
    float GetCurrentConfidence() const;

    /**
     * Get current agent state string.
     */
    UFUNCTION(BlueprintPure, Category = "Sarembok|Demo")
    FString GetCurrentAgentState() const;

    /**
     * Deterministically spawn a SarembokDemoStimulusActor into the world.
     */
    UFUNCTION(BlueprintCallable, Category = "Sarembok|Demo")
    ASarembokDemoStimulusActor* SpawnDemoStimulusActor();

    /**
     * Inject an action failure for testing failure recovery and replanning state transition.
     */
    UFUNCTION(BlueprintCallable, Category = "Sarembok|Demo")
    void InjectDemoFailure();

private:
    UPROPERTY()
    ASarembokDemoStimulusActor* SpawnedStimulusActor;

    FSarembokIntent LastIntentCache;
};
