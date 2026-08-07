#include "SarembokAvatarController.h"

USarembokAvatarController::USarembokAvatarController()
{
    PrimaryComponentTick.bCanEverTick = false;
    CurrentEmotion = TEXT("Neutral");
}

void USarembokAvatarController::SetEmotion(const FString& Emotion)
{
    CurrentEmotion = Emotion;

    UE_LOG(LogTemp, Log,
        TEXT("Sarembok Avatar Emotion: %s"),
        *Emotion);
}

void USarembokAvatarController::LookAtTarget(AActor* Target)
{
    if (Target)
    {
        UE_LOG(LogTemp, Log,
            TEXT("Sarembok Avatar Looking At: %s"),
            *Target->GetName());
    }
}

FString USarembokAvatarController::GetCurrentEmotion() const
{
    return CurrentEmotion;
}
