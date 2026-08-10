#pragma once

#include "CoreMinimal.h"
#include "SarembokReasoningProvider.h"
#include "SarembokDeterministicReasoner.h"

/**
 * External LLM / AI Reasoning Provider.
 * Connects to external AI endpoints (Gemini Live / WebSocket server).
 * Features an integrated deterministic fallback reasoner for offline resilience.
 */
class SAREMBOKAGENT_API FSarembokLLMReasoner : public ISarembokReasoningProvider
{
public:

    FSarembokLLMReasoner(bool bEnableAI = false, const FString& Endpoint = TEXT("ws://127.0.0.1:9000"));

    virtual FSarembokIntent ReasonWithGoal(
        const FSarembokWorldDelta& Delta,
        const FSarembokGoal& ActiveGoal,
        const TArray<FSarembokEpisode>& RecentEpisodes,
        int32 IdleCycles
    ) override;

    virtual FString GetProviderName() const override
    {
        return bAIOnline ? TEXT("LLMReasoner[Online]") : TEXT("LLMReasoner[Fallback]");
    }

    void SetAIOnline(bool bOnline)
    {
        bAIOnline = bOnline;
    }

    bool IsAIOnline() const
    {
        return bAIOnline;
    }

private:

    bool bAIOnline = false;
    FString ServerEndpoint;
    FSarembokDeterministicReasoner FallbackReasoner;

    FString FormatLLMPrompt(
        const FSarembokWorldDelta& Delta,
        const FSarembokGoal& ActiveGoal,
        const TArray<FSarembokEpisode>& RecentEpisodes
    ) const;
};
