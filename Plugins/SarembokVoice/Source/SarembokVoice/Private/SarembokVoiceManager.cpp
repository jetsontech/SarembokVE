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
    ActiveVisemeWeight = CalculateVisemeWeight(Text);

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] VOICE EXECUTED | Status=Executed | Text=%s"),
        *Text
    );

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][VOICE] VISEME_WEIGHT Weight=%.2f Speech=%s"),
        ActiveVisemeWeight,
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

float USarembokVoiceManager::CalculateVisemeWeight(const FString& Speech) const
{
    if (Speech.IsEmpty())
    {
        return 0.0f;
    }

    int32 VowelCount = 0;
    for (TCHAR Ch : Speech.ToLower())
    {
        if (Ch == 'a' || Ch == 'e' || Ch == 'i' || Ch == 'o' || Ch == 'u')
        {
            VowelCount++;
        }
    }

    float Ratio = static_cast<float>(VowelCount) / FMath::Max(1, Speech.Len());
    return FMath::Clamp(0.5f + Ratio * 0.8f, 0.4f, 0.95f);
}

float USarembokVoiceManager::GetActiveVisemeWeight() const
{
    return CurrentSpeech.IsEmpty() ? 0.0f : ActiveVisemeWeight;
}

int32 USarembokVoiceManager::GetSpeechQueueCount() const
{
    return SpeechQueue.Num();
}
