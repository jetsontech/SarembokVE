// SarembokGovernanceModule.h
#pragma once
#include "Modules/ModuleManager.h"

class FSarembokGovernanceModule : public IModuleInterface
{
public:
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;
};
