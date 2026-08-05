#include "SarembokRuntimeManager.h"


FSarembokRuntimeManager::
FSarembokRuntimeManager()
{
}



FSarembokRuntimeManager&
FSarembokRuntimeManager::Get()
{
    static FSarembokRuntimeManager Instance;

    return Instance;
}



void FSarembokRuntimeManager::Initialize()
{
    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Runtime Manager Initialized")
    );
}



void FSarembokRuntimeManager::Shutdown()
{
}
