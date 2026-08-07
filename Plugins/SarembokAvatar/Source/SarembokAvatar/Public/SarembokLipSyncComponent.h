#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SarembokLipSyncComponent.generated.h"

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKAVATAR_API USarembokLipSyncComponent : public UActorComponent
{
    GENERATED_BODY()

public:

    UFUNCTION(BlueprintCallable, Category="Sarembok Voice")
    void ProcessSpeech(const FString& Text);

};
