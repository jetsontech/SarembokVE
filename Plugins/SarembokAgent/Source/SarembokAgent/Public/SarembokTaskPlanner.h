#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "SarembokTaskPlanner.generated.h"

USTRUCT(BlueprintType)
struct FSarembokPlanStep
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite)
    FString Action;

    UPROPERTY(BlueprintReadWrite)
    FString Target;

    UPROPERTY(BlueprintReadWrite)
    FString Parameters;
};

UCLASS(Blueprintable)
class SAREMBOKAGENT_API USarembokTaskPlanner : public UObject
{
    GENERATED_BODY()

public:

    UFUNCTION(BlueprintCallable, Category="Sarembok Planner")
    TArray<FSarembokPlanStep> BuildPlan(
        const FString& Intent,
        const FString& Context
    );

private:
    TArray<FSarembokPlanStep> ActivePlan;
};
