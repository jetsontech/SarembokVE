#pragma once

#include "CoreMinimal.h"
#include "SarembokReasoningProvider.h"

/**
 * Deterministic rule-based reasoning provider.
 * Produces predictable, scored intents based on world delta and active goal context.
 */
class FSarembokDeterministicReasoner : public ISarembokReasoningProvider
{
public:

    virtual FSarembokIntent ReasonWithGoal(
        const FSarembokWorldDelta& Delta,
        const FSarembokGoal& ActiveGoal,
        const TArray<FSarembokEpisode>& RecentEpisodes,
        int32 IdleCycles
    ) override;

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
