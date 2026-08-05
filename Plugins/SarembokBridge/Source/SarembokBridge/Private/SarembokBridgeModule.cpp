#include "SarembokBridgeModule.h"
#include "SarembokRuntimeManager.h"


void FSarembokBridgeModule::StartupModule()
{

UE_LOG(
LogTemp,
Display,
TEXT("Sarembok Bridge Initialized")
);


USarembokRuntimeManager* Runtime =
NewObject<USarembokRuntimeManager>();

Runtime->InitializeRuntime();

}



void FSarembokBridgeModule::ShutdownModule()
{

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
