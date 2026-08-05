#include "SarembokMemory.h"

void FSarembokMemory::StartupModule()
{

    UE_LOG(
        LogTemp,
        Display,
        TEXT("SarembokMemory Initialized")
    );

}


void FSarembokMemory::ShutdownModule()
{

    UE_LOG(
        LogTemp,
        Display,
        TEXT("SarembokMemory Shutdown")
    );

}


IMPLEMENT_MODULE(
    FSarembokMemory,
    SarembokMemory
)
