#include "SarembokRuntimeManager.h"

void USarembokRuntimeManager::InitializeRuntime()
{
    if (bInitialized)
    {
        return;
    }

    bInitialized = true;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Runtime Manager Initialized")
    );
}

void USarembokRuntimeManager::ShutdownRuntime()
{
    if (!bInitialized)
    {
        return;
    }

    bInitialized = false;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Runtime Manager Shutdown")
    );
}
