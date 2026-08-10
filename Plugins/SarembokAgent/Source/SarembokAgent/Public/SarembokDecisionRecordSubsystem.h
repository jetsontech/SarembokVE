// ============================================================
// SarembokDecisionRecordSubsystem.h
// Structured Cognitive Decision Record Subsystem
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokDecisionRecordSubsystem.generated.h"

USTRUCT(BlueprintType)
struct FSarembokDecisionRecord
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Observability")
    FString DecisionId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Observability")
    FString TraceId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Observability")
    FString UserId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Observability")
    FString ConversationId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Observability")
    FString PerceptionSummary;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Observability")
    FString GoalSummary;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Observability")
    int32 RetrievedMemoryCount = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Observability")
    float ReasoningConfidence = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Observability")
    TArray<FString> CandidateActions;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Observability")
    FString PolicyResult;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Observability")
    FString SelectedAction;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|Observability")
    FString Outcome;
};

UCLASS()
class SAREMBOKAGENT_API USarembokDecisionRecordSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category = "Sarembok|Observability")
    void RecordDecision(const FSarembokDecisionRecord& Record);

    UFUNCTION(BlueprintPure, Category = "Sarembok|Observability")
    TArray<FSarembokDecisionRecord> GetRecentDecisionRecords(int32 MaxCount = 10) const;

private:

    TArray<FSarembokDecisionRecord> DecisionHistory;
};
