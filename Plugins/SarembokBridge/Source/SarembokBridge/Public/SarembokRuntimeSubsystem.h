#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokRuntimeSubsystem.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnSarembokSpeakSignature, const FString&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnSarembokEmotionSignature, const FString&, Emotion);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnSarembokObserveSignature, const FString&, Target);

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

    UPROPERTY(BlueprintAssignable, Category="Sarembok|Events")
    FOnSarembokSpeakSignature OnSpeak;

    UPROPERTY(BlueprintAssignable, Category="Sarembok|Events")
    FOnSarembokEmotionSignature OnEmotionSet;

    UPROPERTY(BlueprintAssignable, Category="Sarembok|Events")
    FOnSarembokObserveSignature OnObserve;

private:
    bool bInitialized = false;
};
