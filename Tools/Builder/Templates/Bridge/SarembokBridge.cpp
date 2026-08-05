#include "Modules/ModuleManager.h"


class FSarembokBridgeModule :
    public IModuleInterface
{

public:

    virtual void StartupModule() override
    {
        UE_LOG(
            LogTemp,
            Display,
            TEXT("Sarembok Bridge Initialized")
        );
    }


    virtual void ShutdownModule() override
    {
        UE_LOG(
            LogTemp,
            Display,
            TEXT("Sarembok Bridge Shutdown")
        );
    }

};


IMPLEMENT_MODULE(
    FSarembokBridgeModule,
    SarembokBridge
)
