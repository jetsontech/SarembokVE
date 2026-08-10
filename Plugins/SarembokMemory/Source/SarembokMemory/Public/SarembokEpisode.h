#pragma once

#include "CoreMinimal.h"
#include "SarembokEpisode.generated.h"

USTRUCT(BlueprintType)
struct SAREMBOKMEMORY_API FSarembokEpisode
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Memory")
    FDateTime Timestamp;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Memory")
    FString EventType; // "ActorAdded", "ActorRemoved", "ActorMoved", "EmotionChanged", "SpeechExecuted", "AgentAction"

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Memory")
    FString ActorId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Memory")
    FString Description;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Memory")
    FString ActionTaken;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Memory")
    FString Outcome;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Memory")
    FString TraceId;
};
