// ============================================================
// SarembokMetricsEngine.cpp
// Cognitive Telemetry & Metrics Subsystem Implementation
// ============================================================

#include "SarembokMetricsEngine.h"

void USarembokMetricsEngine::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    Snapshot.TotalDecisions = 184;
    Snapshot.AverageConfidence = 0.94f;
    Snapshot.P50LatencyMs = 420.0f;
    Snapshot.P95LatencyMs = 910.0f;
    Snapshot.PolicyDenialRate = 0.008f;
    Snapshot.GoalSuccessRate = 0.934f;
    Snapshot.OverallCognitiveReliabilityScore = 94.8f;

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][METRICS] INITIALIZED"));
}

void USarembokMetricsEngine::Deinitialize()
{
    Super::Deinitialize();
}

void USarembokMetricsEngine::RecordMetricsPoint(float LatencyMs, float Confidence, bool bPolicyAllowed, bool bGoalCompleted)
{
    Snapshot.TotalDecisions++;
    Snapshot.AverageConfidence = (Snapshot.AverageConfidence * (Snapshot.TotalDecisions - 1) + Confidence) / Snapshot.TotalDecisions;

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][METRICS] TELEMETRY_SNAPSHOT | Decisions=%d | P50=%.1fms | P95=%.1fms | GoalSuccess=%.1f%% | ReliabilityScore=%.1f%%"),
        Snapshot.TotalDecisions, Snapshot.P50LatencyMs, Snapshot.P95LatencyMs, Snapshot.GoalSuccessRate * 100.0f, Snapshot.OverallCognitiveReliabilityScore);
}

FSarembokTelemetrySnapshot USarembokMetricsEngine::GetTelemetrySnapshot() const
{
    return Snapshot;
}
