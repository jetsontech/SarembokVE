#include "Modules/ModuleManager.h"

class FSarembokAvatarModule : public IModuleInterface
{
public:
    virtual void StartupModule() override {}
    virtual void ShutdownModule() override {}
};

IMPLEMENT_MODULE(FSarembokAvatarModule, SarembokAvatar)
