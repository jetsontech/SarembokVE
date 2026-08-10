#pragma once

#include "CoreMinimal.h"
#include "SarembokReasoningProvider.h"

/**
 * Deterministic rule-based reasoning provider for v1.2.0-alpha.
 * Produces predictable, testable intents based on world delta patterns.
 */
class FSarembokDeterministicReasoner : public ISarembokReasoningProvider
{
public:

    virtual FSarembokIntent Reason(
        const FSarembokWorldDelta& Delta,
        const TArray<FSarembokEpisode>& RecentEpisodes,
        int32 IdleCycles
    ) override;

    virtual FString GetProviderName() const override
    {
        return TEXT("DeterministicReasoner");
    }
};
