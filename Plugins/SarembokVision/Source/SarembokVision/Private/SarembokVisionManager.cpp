#include "SarembokVisionManager.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Actor.h"

void USarembokVisionManager::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    Observations.Empty();
    FrameCounter = 0;

    UE_LOG(LogTemp, Display, TEXT("Sarembok Vision Runtime Initialized"));
}

void USarembokVisionManager::Deinitialize()
{
    Observations.Empty();
    Super::Deinitialize();
}

void USarembokVisionManager::ObserveScene()
{
    Observations.Empty();

    UWorld* World = GetWorld();
    if (World)
    {
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            AActor* Actor = *It;
            if (Actor && !Actor->IsPendingKillPending() && !Actor->GetName().StartsWith(TEXT("Default__")))
            {
                FSarembokObservation Obs;
                Obs.ObjectName = Actor->GetName();
                Obs.Confidence = 1.0f;
                Obs.Location   = Actor->GetActorLocation();

                Observations.Add(Obs);

                if (Observations.Num() >= 20)
                {
                    break;
                }
            }
        }
    }

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] VISION SCENE OBSERVED | Visible Objects=%d"),
        Observations.Num()
    );
}

TArray<FSarembokObservation> USarembokVisionManager::GetObservations() const
{
    return Observations;
}

bool USarembokVisionManager::CaptureFrame(FString& OutFrameId)
{
    FrameCounter++;
    OutFrameId = FString::Printf(TEXT("Frame_%06d"), FrameCounter);

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] VISION FRAME CAPTURED | FrameId=%s"),
        *OutFrameId
    );

    return true;
}
