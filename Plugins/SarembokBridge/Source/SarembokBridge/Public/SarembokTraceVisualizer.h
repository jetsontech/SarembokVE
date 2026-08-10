// ============================================================
// SarembokTraceVisualizer.h
// Developer-Facing Execution Trace HUD Overlay
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokTraceVisualizer.generated.h"

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKBRIDGE_API ASarembokTraceVisualizer : public AActor
{
    GENERATED_BODY()

public:
    ASarembokTraceVisualizer();

    virtual void BeginPlay() override;
    virtual void Tick(float DeltaTime) override;

    UFUNCTION(Exec, Category="Sarembok|Trace")
    void ToggleTraceHUD();

    UFUNCTION(BlueprintCallable, Category="Sarembok|Trace")
    void LogExecutionTraceCascade(const FString& TraceId, const FString& GoalDesc, const FString& IntentAction, float Confidence);

private:
    UPROPERTY(EditAnywhere, Category="Sarembok|Trace")
    bool bHUDEnabled = true;

    FString ActiveTraceSummary;
};
