#pragma once

#include "CoreMinimal.h"
#include "SarembokVisionManager.h"
#include "SarembokEpisode.h"

/**
 * Intent produced by a reasoning provider.
 * Represents a single action the agent wants to perform.
 */
struct FSarembokIntent
{
    FString ActionType;   // "Emotion", "Speak", "Observe", "Wait"
    FString Target;       // "Avatar", "Voice", "System"
    FString EmotionState; // for Emotion actions
    FString SpeechText;   // for Speak actions
    FString Reason;       // human-readable explanation
    bool bShouldAct = false;
};

/**
 * Abstract reasoning provider interface.
 * Implementations can be deterministic rules (v1.2.0-alpha) or LLM-backed (future).
 */
class ISarembokReasoningProvider
{
public:
    virtual ~ISarembokReasoningProvider() = default;

    /**
     * Given a world delta and recent episodic context, produce an intent.
     */
    virtual FSarembokIntent Reason(
        const FSarembokWorldDelta& Delta,
        const TArray<FSarembokEpisode>& RecentEpisodes,
        int32 IdleCycles
    ) = 0;

    virtual FString GetProviderName() const = 0;
};
