#pragma once

#include "CoreMinimal.h"
#include "SarembokMessage.generated.h"

USTRUCT(BlueprintType)
struct SAREMBOKBRIDGE_API FSarembokMessage
{
    GENERATED_BODY()

public:

    UPROPERTY(BlueprintReadWrite, Category="Sarembok")
    FString Event;

    UPROPERTY(BlueprintReadWrite, Category="Sarembok")
    FString Source;

    UPROPERTY(BlueprintReadWrite, Category="Sarembok")
    FString Data;

    UPROPERTY(BlueprintReadWrite, Category="Sarembok")
    double Timestamp = 0.0;

    bool IsValid() const
    {
        return !Event.IsEmpty();
    }
};
