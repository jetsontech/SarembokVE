#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokAvatarActor.generated.h"

class USarembokAvatarComponent;

UCLASS(Blueprintable)
class SAREMBOKAVATAR_API ASarembokAvatarActor : public AActor
{
    GENERATED_BODY()

public:
    ASarembokAvatarActor();

    UFUNCTION(BlueprintPure, Category="Sarembok|Avatar")
    USarembokAvatarComponent* GetAvatarComponent() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void Speak(const FString& Text);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void SetEmotion(const FString& Emotion, float Intensity = 1.0f);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void LookAt(const FVector& WorldLocation);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void Gesture(const FString& GestureName);

protected:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Sarembok|Avatar")
    TObjectPtr<USarembokAvatarComponent> AvatarComponent;
};
