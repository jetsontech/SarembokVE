// SarembokCoreModule.cpp
#include "SarembokCoreModule.h"
#include "Modules/ModuleManager.h"

void FSarembokCoreModule::StartupModule()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][CORE] Platform Runtime v2.0 initializing..."));
}

void FSarembokCoreModule::ShutdownModule()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][CORE] Platform Runtime v2.0 shutting down."));
}

IMPLEMENT_MODULE(FSarembokCoreModule, SarembokCore)
