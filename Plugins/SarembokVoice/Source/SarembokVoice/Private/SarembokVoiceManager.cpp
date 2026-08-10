#include "SarembokVoiceManager.h"

void USarembokVoiceManager::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    CurrentSpeech = TEXT("");
    bVoiceAvailable = true;

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Voice Subsystem Initialized"));
}

void USarembokVoiceManager::Deinitialize()
{
    bVoiceAvailable = false;
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Voice Subsystem Deinitialized"));

    Super::Deinitialize();
}

void USarembokVoiceManager::Speak(const FString& Text)
{
    SpeakWithResult(Text);
}

ESarembokVoiceStatus USarembokVoiceManager::SpeakWithResult(const FString& Text)
{
    if (!bVoiceAvailable)
    {
        UE_LOG(LogTemp, Warning, TEXT("[SAREMBOK] VOICE EXECUTOR UNAVAILABLE | Text=%s"), *Text);
        return ESarembokVoiceStatus::Unavailable;
    }

    if (Text.IsEmpty())
    {
        UE_LOG(LogTemp, Warning, TEXT("[SAREMBOK] VOICE EXECUTION FAILED | Empty text payload"));
        return ESarembokVoiceStatus::Failed;
    }

    CurrentSpeech = Text;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] VOICE EXECUTED | Status=Executed | Text=%s"),
        *Text
    );

    return ESarembokVoiceStatus::Executed;
}

bool USarembokVoiceManager::IsVoiceAvailable() const
{
    return bVoiceAvailable;
}

FString USarembokVoiceManager::GetCurrentSpeech() const
{
    return CurrentSpeech;
}
