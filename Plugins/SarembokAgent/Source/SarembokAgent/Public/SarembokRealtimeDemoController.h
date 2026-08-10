// ============================================================
// SarembokRealtimeDemoController.h
// Real-Time Cognitive Interaction Harness Actor (Checks 116 to 140)
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokRealtimeDemoController.generated.h"

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKAGENT_API ASarembokRealtimeDemoController : public AActor
{
    GENERATED_BODY()

public:

    ASarembokRealtimeDemoController();

    virtual void BeginPlay() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|RealtimeDemo")
    void TriggerRealtimeTest_116_120();

    UFUNCTION(BlueprintCallable, Category="Sarembok|RealtimeDemo")
    void TriggerRealtimeTest_121_125();

    UFUNCTION(BlueprintCallable, Category="Sarembok|RealtimeDemo")
    void TriggerRealtimeTest_126_130();

    UFUNCTION(BlueprintCallable, Category="Sarembok|RealtimeDemo")
    void TriggerRealtimeTest_131_135();

    UFUNCTION(BlueprintCallable, Category="Sarembok|RealtimeDemo")
    void TriggerRealtimeTest_136_140();
};
