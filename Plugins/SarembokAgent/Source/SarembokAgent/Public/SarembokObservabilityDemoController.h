// ============================================================
// SarembokObservabilityDemoController.h
// Cognitive Observability Harness Actor (Checks 141 to 165)
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokObservabilityDemoController.generated.h"

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKAGENT_API ASarembokObservabilityDemoController : public AActor
{
    GENERATED_BODY()

public:

    ASarembokObservabilityDemoController();

    virtual void BeginPlay() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|ObservabilityDemo")
    void TriggerObservabilityTest_141_145();

    UFUNCTION(BlueprintCallable, Category="Sarembok|ObservabilityDemo")
    void TriggerObservabilityTest_146_150();

    UFUNCTION(BlueprintCallable, Category="Sarembok|ObservabilityDemo")
    void TriggerObservabilityTest_151_155();

    UFUNCTION(BlueprintCallable, Category="Sarembok|ObservabilityDemo")
    void TriggerObservabilityTest_156_160();

    UFUNCTION(BlueprintCallable, Category="Sarembok|ObservabilityDemo")
    void TriggerObservabilityTest_161_165();
};
