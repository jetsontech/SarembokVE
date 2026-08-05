#pragma once

#include "CoreMinimal.h"

class SAREMBOKBRIDGE_API FSarembokRuntimeManager
{
public:

    static FSarembokRuntimeManager& Get();

    void Initialize();
    void Shutdown();

    bool IsInitialized() const { return bInitialized; }

private:

    FSarembokRuntimeManager();

    bool bInitialized = false;
};
