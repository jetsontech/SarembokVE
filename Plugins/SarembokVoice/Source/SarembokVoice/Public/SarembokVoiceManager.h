#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokVoiceManager.generated.h"

UENUM(BlueprintType)
enum class ESarembokVoiceStatus : uint8
{
    Executed    UMETA(DisplayName = "Executed"),
    Queued      UMETA(DisplayName = "Queued"),
    Unavailable UMETA(DisplayName = "Unavailable"),
    Failed      UMETA(DisplayName = "Failed")
};

UCLASS()
class SAREMBOKVOICE_API USarembokVoiceManager : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok Voice")
    void Speak(const FString& Text);

    UFUNCTION(BlueprintCallable, Category="Sarembok Voice")
    ESarembokVoiceStatus SpeakWithResult(const FString& Text);

    UFUNCTION(BlueprintPure, Category="Sarembok Voice")
    bool IsVoiceAvailable() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok Voice")
    FString GetCurrentSpeech() const;

    UFUNCTION(BlueprintPure, Category="Sarembok Voice")
    float GetActiveVisemeWeight() const;

    UFUNCTION(BlueprintPure, Category="Sarembok Voice")
    int32 GetSpeechQueueCount() const;

private:
    float CalculateVisemeWeight(const FString& Speech) const;

    FString CurrentSpeech;
    float ActiveVisemeWeight = 0.0f;
    bool bVoiceAvailable = true;
    TArray<FString> SpeechQueue;
};
