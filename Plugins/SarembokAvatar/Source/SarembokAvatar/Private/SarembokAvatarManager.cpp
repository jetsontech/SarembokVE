#include "SarembokAvatarManager.h"

USarembokAvatarManager::USarembokAvatarManager()
    : CurrentState(ESarembokAvatarState::Uninitialized)
{
    CurrentEmotion.Name = TEXT("neutral");
    CurrentEmotion.Intensity = 0.0f;
}

void USarembokAvatarManager::InitializeAvatar()
{
    CurrentState = ESarembokAvatarState::Ready;

    UE_LOG(LogTemp, Display, TEXT("Sarembok Avatar Runtime Initialized"));
}

void USarembokAvatarManager::ShutdownAvatar()
{
    CurrentState = ESarembokAvatarState::Disabled;

    UE_LOG(LogTemp, Display, TEXT("Sarembok Avatar Runtime Shutdown"));
}

void USarembokAvatarManager::SetAvatarState(ESarembokAvatarState NewState)
{
    CurrentState = NewState;
}

ESarembokAvatarState USarembokAvatarManager::GetAvatarState() const
{
    return CurrentState;
}

void USarembokAvatarManager::TriggerExpression(const FString& ExpressionName)
{
    UE_LOG(LogTemp, Display, TEXT("Avatar Expression: %s"), *ExpressionName);
}

void USarembokAvatarManager::SetEmotion(const FString& Emotion, float Intensity)
{
    CurrentEmotion.Name = Emotion.IsEmpty() ? TEXT("neutral") : Emotion;
    CurrentEmotion.Intensity = FMath::Clamp(Intensity, 0.0f, 1.0f);

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Avatar Emotion: %s | Intensity: %.2f"),
        *CurrentEmotion.Name,
        CurrentEmotion.Intensity
    );
}

FSarembokEmotionState USarembokAvatarManager::GetEmotion() const
{
    return CurrentEmotion;
}

void USarembokAvatarManager::SynchronizeVoice(const FString& AudioReference)
{
    CurrentState = ESarembokAvatarState::Speaking;

    UE_LOG(LogTemp, Display, TEXT("Avatar Voice Sync: %s"), *AudioReference);
}
