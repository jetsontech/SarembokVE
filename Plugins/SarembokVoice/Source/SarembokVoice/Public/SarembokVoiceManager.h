#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokVoiceManager.generated.h"

UCLASS()
class SAREMBOKVOICE_API USarembokVoiceManager : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok Voice")
    void Speak(const FString& Text);

    UFUNCTION(BlueprintCallable, Category="Sarembok Voice")
    FString GetCurrentSpeech() const;

private:

    FString CurrentSpeech;
};
