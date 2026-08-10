#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokDemoStimulusActor.generated.h"

UCLASS()
class SAREMBOKAGENT_API ASarembokDemoStimulusActor : public AActor
{
    GENERATED_BODY()

public:
    ASarembokDemoStimulusActor();

protected:
    virtual void BeginPlay() override;
};
