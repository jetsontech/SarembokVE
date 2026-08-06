#pragma once

#include "Modules/ModuleManager.h"

class FSarembokBridgeModule : public IModuleInterface
{
public:
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;
};
