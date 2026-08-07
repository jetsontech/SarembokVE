#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokVisionManager.generated.h"

USTRUCT(BlueprintType)
struct FSarembokObservation
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite)
    FString ObjectName;

    UPROPERTY(BlueprintReadWrite)
    float Confidence = 0.0f;
};

UCLASS()
class SAREMBOKVISION_API USarembokVisionManager : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    UFUNCTION(BlueprintCallable, Category="Sarembok Vision")
    void ObserveScene();

    UFUNCTION(BlueprintCallable, Category="Sarembok Vision")
    TArray<FSarembokObservation> GetObservations() const;

private:
    TArray<FSarembokObservation> Observations;
};
