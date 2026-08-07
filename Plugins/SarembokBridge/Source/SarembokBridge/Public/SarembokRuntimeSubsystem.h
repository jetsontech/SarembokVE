#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokRuntimeSubsystem.generated.h"

UCLASS()
class SAREMBOKBRIDGE_API USarembokRuntimeSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok")
    void Speak(const FString& Message);

    UFUNCTION(BlueprintCallable, Category="Sarembok")
    void SetEmotion(const FString& Emotion);

    UFUNCTION(BlueprintCallable, Category="Sarembok")
    void Observe(const FString& Target);

private:
    bool bInitialized = false;
};
