#include "SarembokRuntimeManager.h"

FSarembokRuntimeManager::FSarembokRuntimeManager()
{
}

FSarembokRuntimeManager& FSarembokRuntimeManager::Get()
{
    static FSarembokRuntimeManager Instance;
    return Instance;
}

void FSarembokRuntimeManager::Initialize()
{
    if (bInitialized)
    {
        return;
    }

    bInitialized = true;

    UE_LOG(LogTemp, Display, TEXT("Sarembok Runtime Manager Initialized"));
}

void FSarembokRuntimeManager::Shutdown()
{
    if (!bInitialized)
    {
        return;
    }

    bInitialized = false;

    UE_LOG(LogTemp, Display, TEXT("Sarembok Runtime Manager Shutdown"));
}
