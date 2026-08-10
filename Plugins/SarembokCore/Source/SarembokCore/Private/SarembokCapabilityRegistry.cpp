// ============================================================
// SarembokCapabilityRegistry.cpp
// Platform Capability Registry — Sarembok_VE v2.0
// ============================================================
#include "SarembokCapabilityRegistry.h"

void USarembokCapabilityRegistry::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    RegisterBuiltinCapabilities();
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][CAPABILITY_REGISTRY] Registry ONLINE | Capabilities=%d"), Registry.Num());
}

void USarembokCapabilityRegistry::RegisterBuiltinCapabilities()
{
    auto AddCap = [&](const FString& Id, const FString& Desc, const FString& Permission,
                      ECapabilityCostClass Cost, ECapabilityRiskLevel Risk,
                      TArray<FString> Prereqs = {})
    {
        FSarembokCapabilityDescriptor Cap;
        Cap.CapabilityId        = Id;
        Cap.Description         = Desc;
        Cap.PermissionRequired  = Permission;
        Cap.CostClass           = Cost;
        Cap.RiskLevel           = Risk;
        Cap.Prerequisites       = Prereqs;
        Cap.ExecutionHandlerName = FString::Printf(TEXT("Execute_%s"), *Id);
        Registry.Add(Id, Cap);
    };

    AddCap(TEXT("Speak"),     TEXT("Generate and deliver spoken output to the user"),        TEXT("agent.speak"),     ECapabilityCostClass::Low,    ECapabilityRiskLevel::Safe);
    AddCap(TEXT("Emote"),     TEXT("Change facial expression or body language"),              TEXT("agent.emote"),     ECapabilityCostClass::Trivial, ECapabilityRiskLevel::Safe);
    AddCap(TEXT("Observe"),   TEXT("Perceive and interpret the surrounding world state"),     TEXT("agent.observe"),   ECapabilityCostClass::Low,    ECapabilityRiskLevel::Safe);
    AddCap(TEXT("Navigate"),  TEXT("Move to a location within the environment"),              TEXT("agent.navigate"),  ECapabilityCostClass::Medium, ECapabilityRiskLevel::Mild);
    AddCap(TEXT("Remember"),  TEXT("Persist a fact or event to long-term memory"),            TEXT("agent.remember"),  ECapabilityCostClass::Low,    ECapabilityRiskLevel::Mild);
    AddCap(TEXT("Retrieve"),  TEXT("Query episodic or semantic memory for relevant context"), TEXT("agent.retrieve"),  ECapabilityCostClass::Low,    ECapabilityRiskLevel::Safe);
    AddCap(TEXT("Query"),     TEXT("Run a structured query against knowledge or memory"),     TEXT("agent.query"),     ECapabilityCostClass::Medium, ECapabilityRiskLevel::Safe);
    AddCap(TEXT("Plan"),      TEXT("Generate and select a multi-step action plan"),           TEXT("agent.plan"),      ECapabilityCostClass::High,   ECapabilityRiskLevel::Moderate, {TEXT("Retrieve"), TEXT("Observe")});
    AddCap(TEXT("Interact"),  TEXT("Initiate or respond to a conversational exchange"),       TEXT("agent.interact"),  ECapabilityCostClass::Medium, ECapabilityRiskLevel::Mild, {TEXT("Speak"), TEXT("Observe")});
}

void USarembokCapabilityRegistry::RegisterCapability(const FSarembokCapabilityDescriptor& Descriptor)
{
    Registry.Add(Descriptor.CapabilityId, Descriptor);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][CAPABILITY_REGISTRY] Registered | CapabilityId=%s | Risk=%d | Cost=%d"),
        *Descriptor.CapabilityId, (int32)Descriptor.RiskLevel, (int32)Descriptor.CostClass);
}

bool USarembokCapabilityRegistry::HasCapability(const FString& CapabilityId) const
{
    return Registry.Contains(CapabilityId);
}

FSarembokCapabilityDescriptor USarembokCapabilityRegistry::GetCapability(const FString& CapabilityId) const
{
    const FSarembokCapabilityDescriptor* Found = Registry.Find(CapabilityId);
    return Found ? *Found : FSarembokCapabilityDescriptor{};
}

TArray<FString> USarembokCapabilityRegistry::GetAllCapabilityIds() const
{
    TArray<FString> Ids;
    Registry.GetKeys(Ids);
    return Ids;
}

TArray<FSarembokCapabilityDescriptor> USarembokCapabilityRegistry::GetCapabilitiesByRiskLevel(ECapabilityRiskLevel MaxRisk) const
{
    TArray<FSarembokCapabilityDescriptor> Result;
    for (const auto& Pair : Registry)
    {
        if ((int32)Pair.Value.RiskLevel <= (int32)MaxRisk)
        {
            Result.Add(Pair.Value);
        }
    }
    return Result;
}
