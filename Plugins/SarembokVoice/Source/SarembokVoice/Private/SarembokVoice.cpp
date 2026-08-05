#include "SarembokVoice.h"

void FSarembokVoice::StartupModule()
{

    UE_LOG(
        LogTemp,
        Display,
        TEXT("SarembokVoice Initialized")
    );

}


void FSarembokVoice::ShutdownModule()
{

    UE_LOG(
        LogTemp,
        Display,
        TEXT("SarembokVoice Shutdown")
    );

}


IMPLEMENT_MODULE(
    FSarembokVoice,
    SarembokVoice
)
