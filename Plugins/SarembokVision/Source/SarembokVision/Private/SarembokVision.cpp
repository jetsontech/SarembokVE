#include "SarembokVision.h"

void FSarembokVision::StartupModule()
{

    UE_LOG(
        LogTemp,
        Display,
        TEXT("SarembokVision Initialized")
    );

}


void FSarembokVision::ShutdownModule()
{

    UE_LOG(
        LogTemp,
        Display,
        TEXT("SarembokVision Shutdown")
    );

}


IMPLEMENT_MODULE(
    FSarembokVision,
    SarembokVision
)
