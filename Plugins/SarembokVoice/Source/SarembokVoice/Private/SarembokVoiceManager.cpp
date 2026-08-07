#include "SarembokVoiceManager.h"

void USarembokVoiceManager::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    CurrentSpeech = TEXT("");

    UE_LOG(LogTemp, Log, TEXT("Sarembok Voice Runtime Initialized"));
}

void USarembokVoiceManager::Speak(const FString& Text)
{
    CurrentSpeech = Text;

    UE_LOG(LogTemp, Log, TEXT("Sarembok Speaking: %s"), *Text);

    // TTS provider integration point.
    // This will connect to MetaHuman audio animation pipeline.
}

FString USarembokVoiceManager::GetCurrentSpeech() const
{
    return CurrentSpeech;
}
