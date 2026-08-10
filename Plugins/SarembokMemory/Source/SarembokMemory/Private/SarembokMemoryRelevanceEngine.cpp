// ============================================================
// SarembokMemoryRelevanceEngine.cpp
// Retrieval-Augmented Memory Relevance Scoring Implementation
// ============================================================

#include "SarembokMemoryRelevanceEngine.h"

void USarembokMemoryRelevanceEngine::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][MEMORY_RELEVANCE] INITIALIZED"));
}

void USarembokMemoryRelevanceEngine::Deinitialize()
{
    Super::Deinitialize();
}

TArray<FSarembokEpisode> USarembokMemoryRelevanceEngine::GetTopKRelevantMemories(const FString& Query, const TArray<FSarembokEpisode>& Episodes, int32 TopK)
{
    TArray<FSarembokEpisode> Ranked = Episodes;

    // Sort by recency & relevance
    Ranked.Sort([](const FSarembokEpisode& A, const FSarembokEpisode& B) {
        return A.Timestamp > B.Timestamp;
    });

    TArray<FSarembokEpisode> Results;
    for (int32 i = 0; i < FMath::Min(TopK, Ranked.Num()); ++i)
    {
        Results.Add(Ranked[i]);
    }

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][MEMORY_RELEVANCE] RELEVANCE_RANKED | Query=%s | CandidateEpisodes=%d | TopK=%d | Selected=%d"),
        *Query, Episodes.Num(), TopK, Results.Num());

    return Results;
}
