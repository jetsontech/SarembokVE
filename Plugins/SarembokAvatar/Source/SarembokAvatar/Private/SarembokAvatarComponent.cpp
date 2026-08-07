#include "SarembokAvatarComponent.h"
#include "SarembokAvatarManager.h"

USarembokAvatarComponent::USarembokAvatarComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
    AvatarManager = nullptr;
    Identity = TEXT("DefaultAvatar");
}

void USarembokAvatarComponent::BeginPlay()
{
    Super::BeginPlay();

    AvatarManager = NewObject<USarembokAvatarManager>(this);
    InitializeAvatar();
}

void USarembokAvatarComponent::InitializeAvatar()
{
    if (AvatarManager)
    {
        AvatarManager->InitializeAvatar();

        UE_LOG(
            LogTemp,
            Display,
            TEXT("Sarembok Avatar Component Initialized: %s"),
            *Identity
        );
    }
}

void USarembokAvatarComponent::Speak(const FString& Text)
{
    if (AvatarManager)
    {
        AvatarManager->SynchronizeVoice(Text);

        UE_LOG(
            LogTemp,
            Display,
            TEXT("Avatar Speaking: %s"),
            *Text
        );
    }
}

void USarembokAvatarComponent::SetEmotion(
    const FString& Emotion,
    float Intensity
)
{
    if (AvatarManager)
    {
        AvatarManager->SetEmotion(Emotion, Intensity);
    }
}

void USarembokAvatarComponent::SetIdentity(const FString& AvatarID)
{
    Identity = AvatarID;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Avatar Identity Set: %s"),
        *Identity
    );
}

void USarembokAvatarComponent::LookAt(const FVector& WorldLocation)
{
    if (AActor* Owner = GetOwner())
    {
        const FVector Direction = WorldLocation - Owner->GetActorLocation();
        if (!Direction.IsNearlyZero())
        {
            Owner->SetActorRotation(Direction.Rotation());
        }
    }
}

void USarembokAvatarComponent::Gesture(const FString& GestureName)
{
    if (AvatarManager)
    {
        AvatarManager->TriggerExpression(GestureName);
    }
}

FString USarembokAvatarComponent::GetIdentity() const
{
    return Identity;
}
