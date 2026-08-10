#include "SarembokMemorySubsystem.h"

void USarembokMemorySubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    FScopeLock Lock(&MemoryLock);
    MemoryStore.Empty();

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Memory Subsystem Initialized"));
}

void USarembokMemorySubsystem::Deinitialize()
{
    FScopeLock Lock(&MemoryLock);
    MemoryStore.Empty();

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Memory Subsystem Deinitialized"));

    Super::Deinitialize();
}

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
