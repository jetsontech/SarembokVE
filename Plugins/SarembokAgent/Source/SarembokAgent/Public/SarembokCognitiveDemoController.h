// ============================================================
// SarembokCognitiveDemoController.h
// Cognitive Runtime Verification Harness Actor (Checks 096 to 115)
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokCognitiveDemoController.generated.h"

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKAGENT_API ASarembokCognitiveDemoController : public AActor
{
    GENERATED_BODY()

public:

    ASarembokCognitiveDemoController();

    virtual void BeginPlay() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|CognitiveDemo")
    void TriggerCognitiveTest_096_099();

    UFUNCTION(BlueprintCallable, Category="Sarembok|CognitiveDemo")
    void TriggerCognitiveTest_100_102();

    UFUNCTION(BlueprintCallable, Category="Sarembok|CognitiveDemo")
    void TriggerCognitiveTest_103_105();

    UFUNCTION(BlueprintCallable, Category="Sarembok|CognitiveDemo")
    void TriggerCognitiveTest_106_111();

    UFUNCTION(BlueprintCallable, Category="Sarembok|CognitiveDemo")
    void TriggerCognitiveTest_112_115();
};
