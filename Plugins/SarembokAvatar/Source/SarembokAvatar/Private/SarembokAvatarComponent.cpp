
// ============================================================
// SarembokAvatarComponent.cpp
// ============================================================

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


    AvatarManager = NewObject<USarembokAvatarManager>(
        this
    );


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



void USarembokAvatarComponent::Speak(
    FString Text
)
{
    if (AvatarManager)
    {
        AvatarManager->SynchronizeVoice(
            Text
        );


        UE_LOG(
            LogTemp,
            Display,
            TEXT("Avatar Speaking: %s"),
            *Text
        );
    }
}



void USarembokAvatarComponent::SetIdentity(
    FString AvatarID
)
{
    Identity = AvatarID;


    UE_LOG(
        LogTemp,
        Display,
        TEXT("Avatar Identity Set: %s"),
        *Identity
    );
}

