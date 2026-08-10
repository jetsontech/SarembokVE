// ============================================================
// SarembokTraceViewerComponent.h
// Cognitive Trace Timeline Inspector Component
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SarembokTraceViewerComponent.generated.h"

USTRUCT(BlueprintType)
struct FSarembokTraceStep
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Trace")
    double TimestampMs = 0.0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Trace")
    FString Stage;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Trace")
    FString Message;
};

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKBRIDGE_API USarembokTraceViewerComponent : public UActorComponent
{
    GENERATED_BODY()

public:

    USarembokTraceViewerComponent();

    virtual void BeginPlay() override;

    UFUNCTION(BlueprintCallable, Category = "Sarembok|Trace")
    void LogTraceStep(const FString& Stage, const FString& Message);

    UFUNCTION(BlueprintCallable, Category = "Sarembok|Trace")
    void FormatAndEmitTimeline(const FString& TraceId);

private:

    TArray<FSarembokTraceStep> ActiveTimeline;
};
