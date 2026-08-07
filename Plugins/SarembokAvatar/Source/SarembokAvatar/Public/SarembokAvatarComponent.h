#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SarembokAvatarComponent.generated.h"

class USarembokAvatarManager;

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKAVATAR_API USarembokAvatarComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    USarembokAvatarComponent();

    virtual void BeginPlay() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void InitializeAvatar();

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void Speak(const FString& Text);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void SetEmotion(const FString& Emotion, float Intensity = 1.0f);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void SetIdentity(const FString& AvatarID);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void LookAt(const FVector& WorldLocation);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Avatar")
    void Gesture(const FString& GestureName);

    UFUNCTION(BlueprintPure, Category="Sarembok|Avatar")
    FString GetIdentity() const;

protected:
    UPROPERTY()
    TObjectPtr<USarembokAvatarManager> AvatarManager;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sarembok|Avatar")
    FString Identity;
};
