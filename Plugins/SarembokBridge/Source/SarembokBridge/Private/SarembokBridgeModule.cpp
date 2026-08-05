#include "SarembokBridgeModule.h"
#include "SarembokRuntimeManager.h"

void FSarembokBridgeModule::StartupModule()
{
    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Bridge Initialized")
    );

    FSarembokRuntimeManager::Get().Initialize();
}

void FSarembokBridgeModule::ShutdownModule()
{
    FSarembokRuntimeManager::Get().Shutdown();

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Bridge Shutdown")
    );
}

IMPLEMENT_MODULE(
    FSarembokBridgeModule,
    SarembokBridge
)
