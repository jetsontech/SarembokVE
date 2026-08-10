#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokMemoryInterface.h"
#include "SarembokMemorySubsystem.generated.h"

UCLASS()
class SAREMBOKMEMORY_API USarembokMemorySubsystem : public UGameInstanceSubsystem, public ISarembokMemoryInterface
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    // ISarembokMemoryInterface Implementation
    virtual void StoreMemory(const FString& Key, const FString& Value) override;
    virtual FString RecallMemory(const FString& Key) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok Memory")
    void ClearMemory();

    UFUNCTION(BlueprintPure, Category="Sarembok Memory")
    int32 GetMemoryCount() const;

private:

    TMap<FString, FString> MemoryStore;
    mutable FCriticalSection MemoryLock;
};
