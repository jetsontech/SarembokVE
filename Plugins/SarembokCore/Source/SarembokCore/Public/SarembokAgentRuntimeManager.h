// ============================================================
// SarembokAgentRuntimeManager.h
// Multi-Agent Runtime Manager Subsystem — Sarembok_VE v2.1
// ============================================================
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokAgentRuntimeManager.generated.h"

UCLASS()
class SAREMBOKCORE_API USarembokAgentRuntimeManager : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|RuntimeManager")
    bool RegisterAgentRuntime(const FString& AgentId, const FString& RoleName);

    UFUNCTION(BlueprintCallable, Category="Sarembok|RuntimeManager")
    bool IsAgentActive(const FString& AgentId) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|RuntimeManager")
    TArray<FString> GetActiveAgentRuntimes() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok|RuntimeManager")
    bool TerminateAgentRuntime(const FString& AgentId);

private:
    TMap<FString, FString> ActiveAgentRoles;
};
