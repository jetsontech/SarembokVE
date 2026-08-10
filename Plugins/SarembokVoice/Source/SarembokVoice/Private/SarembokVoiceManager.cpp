#include "SarembokVoiceManager.h"

void USarembokVoiceManager::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    CurrentSpeech = TEXT("");
    bVoiceAvailable = true;
    SpeechQueue.Empty();

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Voice Subsystem Initialized"));
}

void USarembokVoiceManager::Deinitialize()
{
    bVoiceAvailable = false;
    SpeechQueue.Empty();

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
    SpeechQueue.Add(Text);

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

float USarembokVoiceManager::GetActiveVisemeWeight() const
{
    // Return speech viseme activation weight when active speech text is present
    return CurrentSpeech.IsEmpty() ? 0.0f : 0.65f;
}

int32 USarembokVoiceManager::GetSpeechQueueCount() const
{
    return SpeechQueue.Num();
}
