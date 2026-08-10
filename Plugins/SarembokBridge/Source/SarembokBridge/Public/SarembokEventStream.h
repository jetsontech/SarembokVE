// ============================================================
// SarembokEventStream.h
// Unified Event Sourcing & Trajectory Logging Subsystem
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokEventStream.generated.h"

/**
 * Standardized Subsystem Event for Unified Event Sourcing.
 */
USTRUCT(BlueprintType)
struct SAREMBOKBRIDGE_API FSarembokEvent
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|EventStream")
    FString EventId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|EventStream")
    FDateTime Timestamp;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|EventStream")
    FString TraceId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|EventStream")
    FString ConversationId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|EventStream")
    FString UserId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|EventStream")
    FString EventType; // "USER_APPROACHED", "GOAL_PUSHED", "INTENT_GENERATED", "COMMAND_ROUTED", "SPEECH_EXECUTED"

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|EventStream")
    FString Source; // "VISION", "AGENT", "MEMORY", "BRIDGE", "AVATAR", "VOICE"

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|EventStream")
    FString Payload; // JSON payload

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|EventStream")
    FString Outcome = TEXT("Dispatched");

    FSarembokEvent()
        : Timestamp(FDateTime::UtcNow())
    {
    }
};

UCLASS()
class SAREMBOKBRIDGE_API USarembokEventStreamSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category = "Sarembok|EventStream")
    void EmitEvent(const FSarembokEvent& Event);

    UFUNCTION(BlueprintCallable, Category = "Sarembok|EventStream")
    TArray<FSarembokEvent> QueryEventsByTraceId(const FString& TraceId) const;

    UFUNCTION(BlueprintCallable, Category = "Sarembok|EventStream")
    TArray<FSarembokEvent> QueryEventsByUserId(const FString& UserId) const;

    UFUNCTION(BlueprintPure, Category = "Sarembok|EventStream")
    int32 GetEventCount() const;

private:

    UPROPERTY()
    TArray<FSarembokEvent> EventStream;

    int32 EventCounter = 0;
};
