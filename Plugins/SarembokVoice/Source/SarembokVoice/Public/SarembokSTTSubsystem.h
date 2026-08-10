// ============================================================
// SarembokSTTSubsystem.h
// Real-Time Speech-to-Text Input Pipeline Subsystem
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokSTTSubsystem.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnSpeechRecognizedSignature, const FString&, TranscribedText, const FString&, UserId);

UCLASS()
class SAREMBOKVOICE_API USarembokSTTSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UPROPERTY(BlueprintAssignable, Category = "Sarembok|Voice")
    FOnSpeechRecognizedSignature OnSpeechRecognized;

    UFUNCTION(BlueprintCallable, Category = "Sarembok|Voice")
    void ProcessAudioStreamBuffer(const TArray<uint8>& AudioPCM, const FString& UserId);

    UFUNCTION(BlueprintCallable, Category = "Sarembok|Voice")
    void ProcessTranscribedText(const FString& TranscribedText, const FString& UserId);

    UFUNCTION(BlueprintPure, Category = "Sarembok|Voice")
    bool IsSTTActive() const;

private:

    bool bSTTActive = true;
};
