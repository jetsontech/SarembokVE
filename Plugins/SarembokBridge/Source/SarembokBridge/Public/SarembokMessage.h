#pragma once

#include "CoreMinimal.h"
#include "SarembokMessage.generated.h"


USTRUCT(BlueprintType)
struct SAREMBOKBRIDGE_API FSarembokMessage
{

    GENERATED_BODY()


public:


    UPROPERTY(BlueprintReadWrite)
    FString Event;


    UPROPERTY(BlueprintReadWrite)
    FString Data;


};