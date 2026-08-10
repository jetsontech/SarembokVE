#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokMemoryInterface.h"
#include "SarembokEpisode.h"
#include "SarembokMemorySubsystem.generated.h"

UENUM(BlueprintType)
enum class EMemoryScope : uint8
{
    Private UMETA(DisplayName="Private"),
    Team    UMETA(DisplayName="Team"),
    Session UMETA(DisplayName="Session"),
    Global  UMETA(DisplayName="Global")
};

UCLASS()
class SAREMBOKMEMORY_API USarembokMemorySubsystem : public UGameInstanceSubsystem, public ISarembokMemoryInterface
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    // ---- v1.1 Semantic/Fact Memory (backward compatible) ----

    virtual void StoreMemory(const FString& Key, const FString& Value) override;
    virtual FString RecallMemory(const FString& Key) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok Memory")
    void StoreScopedMemory(const FString& AgentId, EMemoryScope Scope, const FString& Key, const FString& Value);

    UFUNCTION(BlueprintCallable, Category="Sarembok Memory")
    FString RecallScopedMemory(const FString& AgentId, EMemoryScope Scope, const FString& Key) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok Memory")
    void ClearMemory();

    UFUNCTION(BlueprintPure, Category="Sarembok Memory")
    int32 GetMemoryCount() const;

    // ---- v1.2 Working Memory ----

    UFUNCTION(BlueprintCallable, Category="Sarembok Memory")
    void SetWorkingMemory(const FString& Key, const FString& Value);

    UFUNCTION(BlueprintPure, Category="Sarembok Memory")
    FString GetWorkingMemory(const FString& Key) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok Memory")
    void ClearWorkingMemory();

    // ---- v1.2 Episodic Memory ----

    UFUNCTION(BlueprintCallable, Category="Sarembok Memory")
    void StoreEpisode(const FSarembokEpisode& Episode);

    UFUNCTION(BlueprintCallable, Category="Sarembok Memory")
    TArray<FSarembokEpisode> RecallRecentEpisodes(int32 Count) const;

    UFUNCTION(BlueprintCallable, Category="Sarembok Memory")
    TArray<FSarembokEpisode> RecallEpisodesByType(const FString& EventType, int32 MaxCount) const;

    UFUNCTION(BlueprintPure, Category="Sarembok Memory")
    int32 GetEpisodeCount() const;

private:

    // v1.1 semantic store
    TMap<FString, FString> MemoryStore;

    // v1.2 working memory (short-lived per-cycle context)
    TMap<FString, FString> WorkingMemoryStore;

    // v1.2 episodic memory (timestamped event records)
    TArray<FSarembokEpisode> EpisodicMemory;
    static constexpr int32 MaxEpisodes = 256;

    mutable FCriticalSection MemoryLock;
};
