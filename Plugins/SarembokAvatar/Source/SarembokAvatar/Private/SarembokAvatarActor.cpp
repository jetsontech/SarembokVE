#include "SarembokAvatarActor.h"
#include "SarembokAvatarComponent.h"

ASarembokAvatarActor::ASarembokAvatarActor()
{
    PrimaryActorTick.bCanEverTick = false;

    AvatarComponent = CreateDefaultSubobject<USarembokAvatarComponent>(
        TEXT("SarembokAvatarComponent")
    );
}

USarembokAvatarComponent* ASarembokAvatarActor::GetAvatarComponent() const
{
    return AvatarComponent;
}

void ASarembokAvatarActor::Speak(const FString& Text)
{
    if (AvatarComponent)
    {
        AvatarComponent->Speak(Text);
    }
}

void ASarembokAvatarActor::SetEmotion(
    const FString& Emotion,
    float Intensity
)
{
    if (!AvatarComponent)
    {
        return;
    }

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Avatar Emotion: %s | Intensity: %.2f"),
        *Emotion,
        Intensity
    );
}

void ASarembokAvatarActor::LookAt(const FVector& WorldLocation)
{
    const FVector Direction = WorldLocation - GetActorLocation();

    if (!Direction.IsNearlyZero())
    {
        SetActorRotation(Direction.Rotation());
    }

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Avatar LookAt: %s"),
        *WorldLocation.ToString()
    );
}

void ASarembokAvatarActor::Gesture(const FString& GestureName)
{
    UE_LOG(
        LogTemp,
        Display,
        TEXT("Avatar Gesture: %s"),
        *GestureName
    );
}
