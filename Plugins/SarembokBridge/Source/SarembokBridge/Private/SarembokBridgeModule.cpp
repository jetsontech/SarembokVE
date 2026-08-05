#include "SarembokBridgeModule.h"
#include "SarembokRuntimeManager.h"
#include "UObject/UObjectGlobals.h"

static USarembokRuntimeManager* GSarembokRuntimeManager = nullptr;

void FSarembokBridgeModule::StartupModule()
{
    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Bridge Initialized")
    );

    GSarembokRuntimeManager = NewObject<USarembokRuntimeManager>(
        GetTransientPackage(),
        USarembokRuntimeManager::StaticClass()
    );

    if (GSarembokRuntimeManager)
    {
        GSarembokRuntimeManager->AddToRoot();
        GSarembokRuntimeManager->InitializeRuntime();
    }
}

void FSarembokBridgeModule::ShutdownModule()
{
    if (GSarembokRuntimeManager)
    {
        GSarembokRuntimeManager->ShutdownRuntime();
        GSarembokRuntimeManager->RemoveFromRoot();
        GSarembokRuntimeManager = nullptr;
    }

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
