#pragma once

#include "Modules/ModuleManager.h"

class FSarembokVoice : public IModuleInterface
{

public:

    virtual void StartupModule() override;

    virtual void ShutdownModule() override;

};
