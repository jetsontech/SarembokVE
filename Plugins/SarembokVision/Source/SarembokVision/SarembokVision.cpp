#include "Modules/ModuleManager.h"

class FSarembokVisionModule : public IModuleInterface
{
public:
    virtual void StartupModule() override {}
    virtual void ShutdownModule() override {}
};

IMPLEMENT_MODULE(FSarembokVisionModule, SarembokVision)
