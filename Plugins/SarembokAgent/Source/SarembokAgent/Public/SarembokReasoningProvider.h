#pragma once

#include "CoreMinimal.h"
#include "SarembokVisionManager.h"
#include "SarembokEpisode.h"
#include "SarembokReasoningProvider.generated.h"

/**
 * Autonomous Goal representing a persistent objective.
 */
USTRUCT(BlueprintType)
struct SAREMBOKAGENT_API FSarembokGoal
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString GoalId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString Description;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    int32 Priority = 50; // 1 to 100

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString TargetState; // JSON or human-readable target state description

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    float Progress = 0.0f; // 0.0 to 1.0

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString Status = TEXT("Active"); // "Active", "Completed", "Failed", "Suspended"

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    int32 Attempts = 0;
};

/**
 * Intent produced by a reasoning provider.
 * Represents a single action the agent wants to perform, scored with confidence.
 */
USTRUCT(BlueprintType)
struct SAREMBOKAGENT_API FSarembokIntent
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString ActionType;   // "Emotion", "Speak", "Observe", "Wait"

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString Target;       // "Avatar", "Voice", "System"

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString EmotionState; // for Emotion actions

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString SpeechText;   // for Speak actions

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString Reason;       // human-readable explanation

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    bool bShouldAct = false;

    // v1.3 Confidence & Candidate Scoring
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    float Confidence = 1.0f; // 0.0 to 1.0

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString GoalId; // ID of active goal being pursued

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString PlanId; // Sequence plan ID

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    TArray<FString> AlternativeActions; // Candidate actions considered
};

/**
 * Abstract reasoning provider interface.
 * Implementations can be deterministic rules, LLM-backed (Gemini), or custom AI engines.
 */
class ISarembokReasoningProvider
{
public:
    virtual ~ISarembokReasoningProvider() = default;

    /**
     * Given a world delta, active goal, and recent episodic context, produce a scored intent.
     */
    virtual FSarembokIntent ReasonWithGoal(
        const FSarembokWorldDelta& Delta,
        const FSarembokGoal& ActiveGoal,
        const TArray<FSarembokEpisode>& RecentEpisodes,
        int32 IdleCycles
    ) = 0;

    /**
     * Backward compatible Reason interface (default forwards to ReasonWithGoal with empty goal).
     */
    virtual FSarembokIntent Reason(
        const FSarembokWorldDelta& Delta,
        const TArray<FSarembokEpisode>& RecentEpisodes,
        int32 IdleCycles
    )
    {
        FSarembokGoal DummyGoal;
        return ReasonWithGoal(Delta, DummyGoal, RecentEpisodes, IdleCycles);
    }

    virtual FString GetProviderName() const = 0;
};
