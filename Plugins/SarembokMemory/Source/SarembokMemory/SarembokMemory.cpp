#include "Modules/ModuleManager.h"

class FSarembokMemoryModule : public IModuleInterface
{
public:
    virtual void StartupModule() override {}
    virtual void ShutdownModule() override {}
};

IMPLEMENT_MODULE(FSarembokMemoryModule, SarembokMemory)
