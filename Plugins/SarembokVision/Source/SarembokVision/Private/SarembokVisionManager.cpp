#include "SarembokVisionManager.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Character.h"
#include "GameFramework/Pawn.h"
#include "Components/StaticMeshComponent.h"
#include "Components/LightComponent.h"
#include "SarembokAvatarComponent.h"

void USarembokVisionManager::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    Observations.Empty();
    FrameCounter = 0;
    CurrentWorldState = FSarembokWorldState();
    PreviousWorldState = FSarembokWorldState();
    bHasPreviousState = false;

    UE_LOG(LogTemp, Display, TEXT("Sarembok Vision Runtime Initialized"));
}

void USarembokVisionManager::Deinitialize()
{
    Observations.Empty();
    Super::Deinitialize();
}

// ---- v1.1 backward-compatible implementation ----

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

// ---- v1.2 structured world model implementation ----

FString USarembokVisionManager::ClassifyActorType(const AActor* Actor) const
{
    if (!Actor)
    {
        return TEXT("Unknown");
    }

    if (Actor->IsA<ACharacter>())
    {
        return TEXT("Character");
    }

    if (Actor->IsA<APawn>())
    {
        return TEXT("Pawn");
    }

    if (Actor->FindComponentByClass<UStaticMeshComponent>())
    {
        return TEXT("StaticMesh");
    }

    if (Actor->FindComponentByClass<ULightComponent>())
    {
        return TEXT("Light");
    }

    return TEXT("Other");
}

float USarembokVisionManager::ComputeDistanceFromAvatar(const AActor* Actor, UWorld* World) const
{
    if (!Actor || !World)
    {
        return 0.0f;
    }

    // Find the Sarembok avatar actor for distance reference
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->FindComponentByClass<USarembokAvatarComponent>())
        {
            return FVector::Dist(Actor->GetActorLocation(), It->GetActorLocation());
        }
    }

    return 0.0f;
}

FSarembokWorldState USarembokVisionManager::GetWorldState()
{
    // Rotate: current becomes previous
    PreviousWorldState = CurrentWorldState;
    bHasPreviousState = (CurrentWorldState.ActorCount > 0);

    // Build new current world state
    CurrentWorldState = FSarembokWorldState();
    CurrentWorldState.Timestamp = FDateTime::UtcNow();

    UWorld* World = GetWorld();
    if (!World)
    {
        return CurrentWorldState;
    }

    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (!Actor || Actor->IsPendingKillPending())
        {
            continue;
        }

        // Skip engine default objects and transient actors
        if (Actor->GetName().StartsWith(TEXT("Default__")))
        {
            continue;
        }

        FSarembokActorState ActorState;
        ActorState.ActorId = Actor->GetName();
        ActorState.ActorName = Actor->GetActorLabel().IsEmpty()
            ? Actor->GetName()
            : Actor->GetActorLabel();
        ActorState.ActorType = ClassifyActorType(Actor);
        ActorState.Location = Actor->GetActorLocation();
        ActorState.DistanceFromAvatar = ComputeDistanceFromAvatar(Actor, World);
        ActorState.bVisible = true;
        ActorState.Confidence = 1.0f;

        CurrentWorldState.Actors.Add(ActorState);

        if (CurrentWorldState.Actors.Num() >= 50)
        {
            break;
        }
    }

    CurrentWorldState.ActorCount = CurrentWorldState.Actors.Num();

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][VISION] WORLD_STATE | Actors=%d | Timestamp=%s"),
        CurrentWorldState.ActorCount,
        *CurrentWorldState.Timestamp.ToIso8601()
    );

    // Also populate v1.1 Observations for backward compatibility
    ObserveScene();

    return CurrentWorldState;
}

FSarembokWorldDelta USarembokVisionManager::DetectChanges()
{
    FSarembokWorldDelta Delta;

    if (!bHasPreviousState)
    {
        // First observation — everything is "new" but we don't report it as delta
        return Delta;
    }

    // Build lookup of previous actors by ID
    TMap<FString, FSarembokActorState> PreviousActorMap;
    for (const FSarembokActorState& Prev : PreviousWorldState.Actors)
    {
        PreviousActorMap.Add(Prev.ActorId, Prev);
    }

    // Build lookup of current actors by ID
    TMap<FString, FSarembokActorState> CurrentActorMap;
    for (const FSarembokActorState& Curr : CurrentWorldState.Actors)
    {
        CurrentActorMap.Add(Curr.ActorId, Curr);
    }

    // Detect added and moved actors
    for (const auto& Pair : CurrentActorMap)
    {
        const FSarembokActorState* PrevState = PreviousActorMap.Find(Pair.Key);

        if (!PrevState)
        {
            // Actor added
            FSarembokActorDelta ActorDelta;
            ActorDelta.DeltaType = ESarembokDeltaType::ActorAdded;
            ActorDelta.Actor = Pair.Value;
            Delta.Deltas.Add(ActorDelta);
            Delta.AddedCount++;

            UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][VISION] ACTOR_ADDED Actor=%s"), *Pair.Value.ActorName);
        }
        else
        {
            // Check if moved beyond threshold
            float Dist = FVector::Dist(Pair.Value.Location, PrevState->Location);
            if (Dist > MovementThreshold)
            {
                FSarembokActorDelta ActorDelta;
                ActorDelta.DeltaType = ESarembokDeltaType::ActorMoved;
                ActorDelta.Actor = Pair.Value;
                ActorDelta.PreviousLocation = PrevState->Location;
                Delta.Deltas.Add(ActorDelta);
                Delta.MovedCount++;
            }
        }
    }

    // Detect removed actors
    for (const auto& Pair : PreviousActorMap)
    {
        if (!CurrentActorMap.Contains(Pair.Key))
        {
            FSarembokActorDelta ActorDelta;
            ActorDelta.DeltaType = ESarembokDeltaType::ActorRemoved;
            ActorDelta.Actor = Pair.Value;
            Delta.Deltas.Add(ActorDelta);
            Delta.RemovedCount++;
        }
    }

    Delta.bHasChanges = (Delta.Deltas.Num() > 0);

    if (Delta.bHasChanges)
    {
        UE_LOG(
            LogTemp,
            Display,
            TEXT("[SAREMBOK][VISION] WORLD_DELTA | Changes=%d | Added=%d | Removed=%d | Moved=%d"),
            Delta.Deltas.Num(),
            Delta.AddedCount,
            Delta.RemovedCount,
            Delta.MovedCount
        );
    }

    return Delta;
}

const FSarembokWorldState& USarembokVisionManager::GetPreviousWorldState() const
{
    return PreviousWorldState;
}
