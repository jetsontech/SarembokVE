// ============================================================
// SarembokHardeningDemoController.h
// Cognitive Platform Hardening Harness Actor (Checks 201 to 225)
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokHardeningDemoController.generated.h"

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKCORE_API ASarembokHardeningDemoController : public AActor
{
    GENERATED_BODY()

public:
    ASarembokHardeningDemoController();

    virtual void BeginPlay() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|HardeningDemo")
    void TriggerHardeningTest_201_205();

    UFUNCTION(BlueprintCallable, Category="Sarembok|HardeningDemo")
    void TriggerHardeningTest_206_210();

    UFUNCTION(BlueprintCallable, Category="Sarembok|HardeningDemo")
    void TriggerHardeningTest_211_215();

    UFUNCTION(BlueprintCallable, Category="Sarembok|HardeningDemo")
    void TriggerHardeningTest_216_220();

    UFUNCTION(BlueprintCallable, Category="Sarembok|HardeningDemo")
    void TriggerHardeningTest_221_225();
};
