// ============================================================
// SarembokResilienceManager.h
// Production Resilience & Write-Ahead Log (WAL) — Sarembok VE 3.0
// ============================================================
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokResilienceManager.generated.h"

USTRUCT(BlueprintType)
struct FSarembokWALEntry
{
    GENERATED_BODY()

    UPROPERTY() FString SequenceId;
    UPROPERTY() FString AgentId;
    UPROPERTY() FString EventType;
    UPROPERTY() FString PayloadJson;
    UPROPERTY() FString Timestamp;
};

UCLASS()
class SAREMBOKCORE_API USarembokResilienceManager : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|Resilience")
    FString AppendWALEntry(const FString& AgentId, const FString& EventType, const FString& PayloadJson);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Resilience")
    int32 ReplayWAL();

    UFUNCTION(BlueprintCallable, Category="Sarembok|Resilience")
    bool RecoverStatePostCrash(const FString& ProcessId);

    UFUNCTION(BlueprintCallable, Category="Sarembok|Resilience")
    int32 GetWALEntryCount() const { return WALEntries.Num(); }

private:
    TArray<FSarembokWALEntry> WALEntries;
    int32 NextSequenceId = 1;
};
