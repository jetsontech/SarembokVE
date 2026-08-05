// ============================================================
// SarembokAvatarBlueprintLibrary.cpp
// ============================================================

#include "SarembokAvatarBlueprintLibrary.h"
#include "SarembokAvatarComponent.h"



void USarembokAvatarBlueprintLibrary::InitializeSarembokAvatar(
    USarembokAvatarComponent* Component
)
{
    if (Component)
    {
        Component->InitializeAvatar();
    }
}



void USarembokAvatarBlueprintLibrary::AvatarSpeak(
    USarembokAvatarComponent* Component,
    FString Text
)
{
    if (Component)
    {
        Component->Speak(Text);
    }
}

