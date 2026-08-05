#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokAvatarController.generated.h"


UCLASS()
class SAREMBOKBRIDGE_API ASarembokAvatarController
:
public AActor
{

GENERATED_BODY()


public:

ASarembokAvatarController();


UFUNCTION(BlueprintCallable)
void SendChat(
FString Message
);


};
