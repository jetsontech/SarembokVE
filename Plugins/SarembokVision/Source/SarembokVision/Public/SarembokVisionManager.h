#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokVisionManager.generated.h"

// ---- v1.1 backward-compatible observation (flat) ----

USTRUCT(BlueprintType)
struct FSarembokObservation
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    FString ObjectName;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    float Confidence = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    FVector Location = FVector::ZeroVector;
};

// ---- v1.2 structured world state ----

USTRUCT(BlueprintType)
struct FSarembokActorState
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    FString ActorId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    FString ActorName;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    FString ActorType; // "StaticMesh", "Character", "Pawn", "Light", "Other"

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    FVector Location = FVector::ZeroVector;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    float DistanceFromAvatar = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    bool bVisible = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    float Confidence = 1.0f;
};

USTRUCT(BlueprintType)
struct FSarembokWorldState
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    FDateTime Timestamp;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    int32 ActorCount = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    TArray<FSarembokActorState> Actors;
};

UENUM(BlueprintType)
enum class ESarembokDeltaType : uint8
{
    None        UMETA(DisplayName = "None"),
    ActorAdded  UMETA(DisplayName = "ActorAdded"),
    ActorRemoved UMETA(DisplayName = "ActorRemoved"),
    ActorMoved  UMETA(DisplayName = "ActorMoved")
};

USTRUCT(BlueprintType)
struct FSarembokActorDelta
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    ESarembokDeltaType DeltaType = ESarembokDeltaType::None;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    FSarembokActorState Actor;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    FVector PreviousLocation = FVector::ZeroVector;
};

USTRUCT(BlueprintType)
struct FSarembokWorldDelta
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    bool bHasChanges = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    TArray<FSarembokActorDelta> Deltas;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    int32 AddedCount = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    int32 RemovedCount = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Vision")
    int32 MovedCount = 0;
};

// ---- Vision Manager ----

UCLASS()
class SAREMBOKVISION_API USarembokVisionManager : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    // v1.1 backward-compatible API
    UFUNCTION(BlueprintCallable, Category="Sarembok Vision")
    void ObserveScene();

    UFUNCTION(BlueprintPure, Category="Sarembok Vision")
    TArray<FSarembokObservation> GetObservations() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok Vision")
    bool CaptureFrame(FString& OutFrameId);

    // v1.2 structured world model API
    UFUNCTION(BlueprintCallable, Category="Sarembok Vision")
    FSarembokWorldState GetWorldState();

    UFUNCTION(BlueprintCallable, Category="Sarembok Vision")
    FSarembokWorldDelta DetectChanges();

    UFUNCTION(BlueprintPure, Category="Sarembok Vision")
    const FSarembokWorldState& GetPreviousWorldState() const;

private:

    // v1.1
    TArray<FSarembokObservation> Observations;
    int32 FrameCounter = 0;

    // v1.2
    FSarembokWorldState CurrentWorldState;
    FSarembokWorldState PreviousWorldState;
    bool bHasPreviousState = false;

    static constexpr float MovementThreshold = 50.0f; // units

    FString ClassifyActorType(const AActor* Actor) const;
    float ComputeDistanceFromAvatar(const AActor* Actor, UWorld* World) const;
};
