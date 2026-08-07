#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "SarembokMemoryInterface.generated.h"

UINTERFACE(BlueprintType)
class SAREMBOKMEMORY_API USarembokMemoryInterface : public UInterface
{
    GENERATED_BODY()
};

class SAREMBOKMEMORY_API ISarembokMemoryInterface
{
    GENERATED_BODY()

public:

    virtual void StoreMemory(
        const FString& Key,
        const FString& Value
    ) = 0;

    virtual FString RecallMemory(
        const FString& Key
    ) = 0;
};
