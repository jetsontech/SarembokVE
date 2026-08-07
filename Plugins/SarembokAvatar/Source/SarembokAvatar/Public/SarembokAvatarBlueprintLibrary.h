#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "SarembokAvatarBlueprintLibrary.generated.h"

class USarembokAvatarComponent;

UCLASS()
class SAREMBOKAVATAR_API USarembokAvatarBlueprintLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    static void InitializeSarembokAvatar(USarembokAvatarComponent* Component);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    static void AvatarSpeak(USarembokAvatarComponent* Component, const FString& Text);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    static void AvatarEmotion(USarembokAvatarComponent* Component, const FString& Emotion, float Intensity = 1.0f);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    static void AvatarGesture(USarembokAvatarComponent* Component, const FString& GestureName);
};
