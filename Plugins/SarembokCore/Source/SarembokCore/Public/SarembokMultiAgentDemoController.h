// ============================================================
// SarembokMultiAgentDemoController.h
// Multi-Agent Platform Harness Actor (Checks 226 to 250)
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokMultiAgentDemoController.generated.h"

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKCORE_API ASarembokMultiAgentDemoController : public AActor
{
    GENERATED_BODY()

public:
    ASarembokMultiAgentDemoController();

    virtual void BeginPlay() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|MultiAgentDemo")
    void TriggerMultiAgentTest_226_230();

    UFUNCTION(BlueprintCallable, Category="Sarembok|MultiAgentDemo")
    void TriggerMultiAgentTest_231_235();

    UFUNCTION(BlueprintCallable, Category="Sarembok|MultiAgentDemo")
    void TriggerMultiAgentTest_236_240();

    UFUNCTION(BlueprintCallable, Category="Sarembok|MultiAgentDemo")
    void TriggerMultiAgentTest_241_245();

    UFUNCTION(BlueprintCallable, Category="Sarembok|MultiAgentDemo")
    void TriggerMultiAgentTest_246_250();
};
