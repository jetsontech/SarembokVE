// ============================================================
// SarembokCognitiveContext.h
// Comprehensive Cognitive Context Assembly & Token Accounting
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "SarembokCognitiveContext.generated.h"

/**
 * 10-Source Cognitive Context Envelope for Real LLM Execution & Token Accounting.
 */
USTRUCT(BlueprintType)
struct SAREMBOKAGENT_API FSarembokCognitiveContext
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Cognitive")
    FString PerceptionSummary;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Cognitive")
    FString WorkingMemorySummary;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Cognitive")
    FString EpisodicMemorySummary;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Cognitive")
    FString SemanticFactsSummary;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Cognitive")
    FString SocialProfileSummary;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Cognitive")
    FString ActiveGoalsSummary;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Cognitive")
    FString RecentEventsSummary;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Cognitive")
    FString ConversationSummary;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Cognitive")
    FString AvailableActionsSummary;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Cognitive")
    FString SafetyConstraintsSummary;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Cognitive")
    int32 PromptTokens = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Cognitive")
    int32 CompletionTokens = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Cognitive")
    int32 TotalTokens = 0;
};
