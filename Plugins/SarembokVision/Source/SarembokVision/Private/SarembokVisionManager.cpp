#include "SarembokVisionManager.h"

void USarembokVisionManager::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    UE_LOG(LogTemp, Log, TEXT("Sarembok Vision Runtime Initialized"));
}

void USarembokVisionManager::ObserveScene()
{
    Observations.Empty();

    FSarembokObservation Example;
    Example.ObjectName = TEXT("CameraInputReady");
    Example.Confidence = 1.0f;

    Observations.Add(Example);

    UE_LOG(LogTemp, Log, TEXT("Sarembok Vision Observation Updated"));
}

TArray<FSarembokObservation> USarembokVisionManager::GetObservations() const
{
    return Observations;
}
