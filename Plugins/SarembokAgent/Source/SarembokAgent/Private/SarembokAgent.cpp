#include "SarembokAgent.h"

void FSarembokAgent::StartupModule()
{

    UE_LOG(
        LogTemp,
        Display,
        TEXT("SarembokAgent Initialized")
    );

}


void FSarembokAgent::ShutdownModule()
{

    UE_LOG(
        LogTemp,
        Display,
        TEXT("SarembokAgent Shutdown")
    );

}


IMPLEMENT_MODULE(
    FSarembokAgent,
    SarembokAgent
)
