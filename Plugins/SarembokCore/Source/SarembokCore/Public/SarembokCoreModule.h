// SarembokCoreModule.h
#pragma once
#include "Modules/ModuleManager.h"

class FSarembokCoreModule : public IModuleInterface
{
public:
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;
};
