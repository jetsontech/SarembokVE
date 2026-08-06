#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokBridgeTestActor.generated.h"

UCLASS(Blueprintable, Category = "SarembokBridge")
class SAREMBOKBRIDGE_API ASarembokBridgeTestActor : public AActor
{
    GENERATED_BODY()

public:
    ASarembokBridgeTestActor();

protected:
    virtual void BeginPlay() override;

public:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "SarembokBridge")
    USceneComponent* RootScene;
};
