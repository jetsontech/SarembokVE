#include "SarembokAvatarBlueprintLibrary.h"
#include "SarembokAvatarComponent.h"

void USarembokAvatarBlueprintLibrary::InitializeSarembokAvatar(
    USarembokAvatarComponent* Component)
{
    if (Component)
    {
        Component->InitializeAvatar();
    }
}

void USarembokAvatarBlueprintLibrary::AvatarSpeak(
    USarembokAvatarComponent* Component,
    const FString& Text)
{
    if (Component)
    {
        Component->Speak(Text);
    }
}

void USarembokAvatarBlueprintLibrary::AvatarEmotion(
    USarembokAvatarComponent* Component,
    const FString& Emotion,
    float Intensity)
{
    if (Component)
    {
        Component->SetEmotion(Emotion, Intensity);
    }
}

void USarembokAvatarBlueprintLibrary::AvatarGesture(
    USarembokAvatarComponent* Component,
    const FString& GestureName)
{
    if (Component)
    {
        Component->Gesture(GestureName);
    }
}
