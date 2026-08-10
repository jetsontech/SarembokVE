// ============================================================
// SarembokPlatformDemoController.h
// Cognitive Platform Harness Actor (Checks 166 to 200)
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokPlatformDemoController.generated.h"

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKCORE_API ASarembokPlatformDemoController : public AActor
{
    GENERATED_BODY()

public:
    ASarembokPlatformDemoController();

    virtual void BeginPlay() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformDemo")
    void TriggerPlatformTest_166_170();

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformDemo")
    void TriggerPlatformTest_171_175();

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformDemo")
    void TriggerPlatformTest_176_180();

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformDemo")
    void TriggerPlatformTest_181_185();

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformDemo")
    void TriggerPlatformTest_186_190();

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformDemo")
    void TriggerPlatformTest_191_195();

    UFUNCTION(BlueprintCallable, Category="Sarembok|PlatformDemo")
    void TriggerPlatformTest_196_200();
};
