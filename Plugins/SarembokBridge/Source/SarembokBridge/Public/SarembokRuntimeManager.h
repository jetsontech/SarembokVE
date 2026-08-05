#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "SarembokRuntimeManager.generated.h"

UCLASS()
class SAREMBOKBRIDGE_API USarembokRuntimeManager : public UObject
{
    GENERATED_BODY()

public:
    void InitializeRuntime();
    void ShutdownRuntime();

    bool IsInitialized() const
    {
        return bInitialized;
    }

private:
    bool bInitialized = false;
};
