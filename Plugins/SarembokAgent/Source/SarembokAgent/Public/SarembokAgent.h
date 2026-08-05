#pragma once

#include "Modules/ModuleManager.h"

class FSarembokAgent : public IModuleInterface
{

public:

    virtual void StartupModule() override;

    virtual void ShutdownModule() override;

};
