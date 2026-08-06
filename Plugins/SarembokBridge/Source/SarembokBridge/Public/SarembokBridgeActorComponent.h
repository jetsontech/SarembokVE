#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SarembokBridgeActorComponent.generated.h"

UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class SAREMBOKBRIDGE_API USarembokBridgeActorComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    USarembokBridgeActorComponent();

protected:
    virtual void BeginPlay() override;
};
