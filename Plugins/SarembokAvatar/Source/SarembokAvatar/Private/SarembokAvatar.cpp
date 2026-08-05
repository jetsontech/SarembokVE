#include "SarembokAvatar.h"

void FSarembokAvatar::StartupModule()
{

    UE_LOG(
        LogTemp,
        Display,
        TEXT("SarembokAvatar Initialized")
    );

}


void FSarembokAvatar::ShutdownModule()
{

    UE_LOG(
        LogTemp,
        Display,
        TEXT("SarembokAvatar Shutdown")
    );

}


IMPLEMENT_MODULE(
    FSarembokAvatar,
    SarembokAvatar
)
