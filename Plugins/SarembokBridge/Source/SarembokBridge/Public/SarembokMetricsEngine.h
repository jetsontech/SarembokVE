// ============================================================
// SarembokMetricsEngine.h
// Cognitive Telemetry & Metrics Subsystem
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokMetricsEngine.generated.h"

USTRUCT(BlueprintType)
struct FSarembokTelemetrySnapshot
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Metrics")
    int32 TotalDecisions = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Metrics")
    float AverageConfidence = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Metrics")
    float P50LatencyMs = 420.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Metrics")
    float P95LatencyMs = 910.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Metrics")
    float PolicyDenialRate = 0.008f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Metrics")
    float GoalSuccessRate = 0.934f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Metrics")
    float OverallCognitiveReliabilityScore = 94.8f;
};

UCLASS()
class SAREMBOKBRIDGE_API USarembokMetricsEngine : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category = "Sarembok|Metrics")
    void RecordMetricsPoint(float LatencyMs, float Confidence, bool bPolicyAllowed, bool bGoalCompleted);

    UFUNCTION(BlueprintPure, Category = "Sarembok|Metrics")
    FSarembokTelemetrySnapshot GetTelemetrySnapshot() const;

private:

    FSarembokTelemetrySnapshot Snapshot;
};
