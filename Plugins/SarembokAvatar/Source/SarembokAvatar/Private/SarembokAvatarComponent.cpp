
// ============================================================
// SarembokAvatarComponent.cpp
// ============================================================

#include "SarembokAvatarComponent.h"
#include "SarembokAvatarManager.h"
#include "SarembokVoiceManager.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"


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
            TEXT("[SAREMBOK] Avatar Component Initialized | Identity=%s"),
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
    }

    if (UWorld* World = GetWorld())
    {
        if (UGameInstance* GI = World->GetGameInstance())
        {
            if (USarembokVoiceManager* VoiceMgr = GI->GetSubsystem<USarembokVoiceManager>())
            {
                VoiceMgr->Speak(Text);
            }
        }
    }

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] AVATAR SPEAKING | Identity=%s | Text=%s"),
        *Identity,
        *Text
    );
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

