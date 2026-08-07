#include "Modules/ModuleManager.h"

class FSarembokAgentModule : public IModuleInterface
{
public:
    virtual void StartupModule() override {}
    virtual void ShutdownModule() override {}
};

IMPLEMENT_MODULE(FSarembokAgentModule, SarembokAgent)
