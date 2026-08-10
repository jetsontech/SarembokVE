#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokVisionManager.generated.h"

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

UCLASS()
class SAREMBOKVISION_API USarembokVisionManager : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok Vision")
    void ObserveScene();

    UFUNCTION(BlueprintPure, Category="Sarembok Vision")
    TArray<FSarembokObservation> GetObservations() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok Vision")
    bool CaptureFrame(FString& OutFrameId);

private:

    TArray<FSarembokObservation> Observations;
    int32 FrameCounter = 0;
};
