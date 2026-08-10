#include "SarembokMemorySubsystem.h"

void USarembokMemorySubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    FScopeLock Lock(&MemoryLock);
    MemoryStore.Empty();
    WorkingMemoryStore.Empty();
    EpisodicMemory.Empty();

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Memory Subsystem Initialized"));
}

void USarembokMemorySubsystem::Deinitialize()
{
    FScopeLock Lock(&MemoryLock);
    MemoryStore.Empty();
    WorkingMemoryStore.Empty();
    EpisodicMemory.Empty();

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Memory Subsystem Deinitialized"));

    Super::Deinitialize();
}

// ---- v1.1 Semantic/Fact Memory ----

void USarembokMemorySubsystem::StoreMemory(const FString& Key, const FString& Value)
{
    FScopeLock Lock(&MemoryLock);
    MemoryStore.FindOrAdd(Key) = Value;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] MEMORY STORED | Key=%s | Value=%s"),
        *Key,
        *Value
    );
}

void USarembokMemorySubsystem::StoreScopedMemory(const FString& AgentId, EMemoryScope Scope, const FString& Key, const FString& Value)
{
    FScopeLock Lock(&MemoryLock);
    FString ScopedKey = FString::Printf(TEXT("%s::%d::%s"), *AgentId, (int32)Scope, *Key);
    MemoryStore.FindOrAdd(ScopedKey) = Value;

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] SCOPED MEMORY STORED | Agent=%s | Scope=%d | Key=%s | Value=%s"),
        *AgentId, (int32)Scope, *Key, *Value);
}

FString USarembokMemorySubsystem::RecallScopedMemory(const FString& AgentId, EMemoryScope Scope, const FString& Key) const
{
    FString ScopedKey = FString::Printf(TEXT("%s::%d::%s"), *AgentId, (int32)Scope, *Key);
    if (const FString* Found = MemoryStore.Find(ScopedKey))
    {
        return *Found;
    }
    // Fall back to global scope if not found in private scope
    FString GlobalKey = FString::Printf(TEXT("global::%d::%s"), (int32)EMemoryScope::Global, *Key);
    if (const FString* GlobalFound = MemoryStore.Find(GlobalKey))
    {
        return *GlobalFound;
    }
    return TEXT("");
}

FString USarembokMemorySubsystem::RecallMemory(const FString& Key)
{
    FScopeLock Lock(&MemoryLock);
    const FString* Found = MemoryStore.Find(Key);

    if (Found)
    {
        UE_LOG(
            LogTemp,
            Display,
            TEXT("[SAREMBOK] MEMORY RECALLED | Key=%s | Value=%s"),
            *Key,
            **Found
        );
        return *Found;
    }

    UE_LOG(
        LogTemp,
        Warning,
        TEXT("[SAREMBOK] MEMORY RECALL MISS | Key=%s"),
        *Key
    );

    return TEXT("");
}

void USarembokMemorySubsystem::ClearMemory()
{
    FScopeLock Lock(&MemoryLock);
    MemoryStore.Empty();

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] MEMORY CLEARED"));
}

int32 USarembokMemorySubsystem::GetMemoryCount() const
{
    FScopeLock Lock(&MemoryLock);
    return MemoryStore.Num();
}

// ---- v1.2 Working Memory ----

void USarembokMemorySubsystem::SetWorkingMemory(const FString& Key, const FString& Value)
{
    FScopeLock Lock(&MemoryLock);
    WorkingMemoryStore.FindOrAdd(Key) = Value;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][MEMORY] WORKING_STORED Key=%s Value=%s"),
        *Key,
        *Value
    );
    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][MEMORY] WORKING_UPDATED | Key=%s"),
        *Key
    );
}

FString USarembokMemorySubsystem::GetWorkingMemory(const FString& Key) const
{
    FScopeLock Lock(&MemoryLock);
    const FString* Found = WorkingMemoryStore.Find(Key);
    return Found ? *Found : TEXT("");
}

void USarembokMemorySubsystem::ClearWorkingMemory()
{
    FScopeLock Lock(&MemoryLock);
    WorkingMemoryStore.Empty();
}

// ---- v1.2 Episodic Memory ----

void USarembokMemorySubsystem::StoreEpisode(const FSarembokEpisode& Episode)
{
    FScopeLock Lock(&MemoryLock);

    // FIFO eviction if at capacity
    if (EpisodicMemory.Num() >= MaxEpisodes)
    {
        EpisodicMemory.RemoveAt(0);
    }

    EpisodicMemory.Add(Episode);

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][MEMORY] EPISODE_STORED EventType=%s ActorId=%s TraceId=%s Total=%d"),
        *Episode.EventType,
        *Episode.ActorId,
        *Episode.TraceId,
        EpisodicMemory.Num()
    );
}

TArray<FSarembokEpisode> USarembokMemorySubsystem::RecallRecentEpisodes(int32 Count) const
{
    FScopeLock Lock(&MemoryLock);

    TArray<FSarembokEpisode> Result;
    int32 StartIdx = FMath::Max(0, EpisodicMemory.Num() - Count);
    for (int32 i = StartIdx; i < EpisodicMemory.Num(); ++i)
    {
        Result.Add(EpisodicMemory[i]);
    }

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][MEMORY] EPISODES_RECALLED | Requested=%d | Returned=%d"),
        Count,
        Result.Num()
    );

    return Result;
}

TArray<FSarembokEpisode> USarembokMemorySubsystem::RecallEpisodesByType(const FString& EventType, int32 MaxCount) const
{
    FScopeLock Lock(&MemoryLock);

    TArray<FSarembokEpisode> Result;

    // Search from most recent backward
    for (int32 i = EpisodicMemory.Num() - 1; i >= 0 && Result.Num() < MaxCount; --i)
    {
        if (EpisodicMemory[i].EventType.Equals(EventType, ESearchCase::IgnoreCase))
        {
            Result.Add(EpisodicMemory[i]);
        }
    }

    return Result;
}

int32 USarembokMemorySubsystem::GetEpisodeCount() const
{
    FScopeLock Lock(&MemoryLock);
    return EpisodicMemory.Num();
}
