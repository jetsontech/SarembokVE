#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SarembokAvatarController.generated.h"

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKAVATAR_API USarembokAvatarController : public UActorComponent
{
    GENERATED_BODY()

public:

    USarembokAvatarController();

    UFUNCTION(BlueprintCallable, Category="Sarembok Avatar")
    void SetEmotion(const FString& Emotion);

    UFUNCTION(BlueprintCallable, Category="Sarembok Avatar")
    void LookAtTarget(AActor* Target);

    UFUNCTION(BlueprintCallable, Category="Sarembok Avatar")
    FString GetCurrentEmotion() const;

private:

    FString CurrentEmotion;
};
