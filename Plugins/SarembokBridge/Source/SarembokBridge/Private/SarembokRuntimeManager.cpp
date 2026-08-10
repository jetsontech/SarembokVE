#include "SarembokRuntimeManager.h"
#include "SarembokBridgeService.h"

void USarembokRuntimeManager::InitializeRuntime()
{
    if (bInitialized)
    {
        return;
    }

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Runtime Manager Initializing")
    );

    FSarembokBridgeService::Get().Initialize();

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

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Runtime Manager Shutting Down")
    );

    FSarembokBridgeService::Get().Shutdown();

    bInitialized = false;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Runtime Manager Shutdown")
    );
}