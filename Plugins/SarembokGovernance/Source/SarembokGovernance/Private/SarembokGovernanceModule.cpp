// SarembokGovernanceModule.cpp
#include "SarembokGovernanceModule.h"
#include "Modules/ModuleManager.h"

void FSarembokGovernanceModule::StartupModule()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][GOVERNANCE] Cognitive Governance Engine ONLINE | v2.0"));
}

void FSarembokGovernanceModule::ShutdownModule()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][GOVERNANCE] Governance Engine shutting down."));
}

IMPLEMENT_MODULE(FSarembokGovernanceModule, SarembokGovernance)
