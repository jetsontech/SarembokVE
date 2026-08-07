#include "Modules/ModuleManager.h"

class FSarembokVoiceModule : public IModuleInterface
{
public:
    virtual void StartupModule() override {}
    virtual void ShutdownModule() override {}
};

IMPLEMENT_MODULE(FSarembokVoiceModule, SarembokVoice)
