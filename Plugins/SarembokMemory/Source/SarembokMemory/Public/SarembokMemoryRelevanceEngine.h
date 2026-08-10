// ============================================================
// SarembokMemoryRelevanceEngine.h
// Retrieval-Augmented Memory Relevance Scoring Subsystem
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokEpisode.h"
#include "SarembokMemoryRelevanceEngine.generated.h"

UCLASS()
class SAREMBOKMEMORY_API USarembokMemoryRelevanceEngine : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category = "Sarembok|MemoryRelevance")
    TArray<FSarembokEpisode> GetTopKRelevantMemories(const FString& Query, const TArray<FSarembokEpisode>& Episodes, int32 TopK = 3);
};
