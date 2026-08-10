#include "SarembokDeterministicReasoner.h"

FSarembokIntent FSarembokDeterministicReasoner::Reason(
    const FSarembokWorldDelta& Delta,
    const TArray<FSarembokEpisode>& RecentEpisodes,
    int32 IdleCycles)
{
    FSarembokIntent Intent;

    // Rule 0: Initial perception scan (first cycle ever)
    if (RecentEpisodes.Num() == 0)
    {
        Intent.bShouldAct = true;
        Intent.ActionType = TEXT("Emotion");
        Intent.Target = TEXT("Avatar");
        Intent.EmotionState = TEXT("Calm");
        Intent.Reason = TEXT("Initial autonomous perception scan");
        return Intent;
    }

    // Rule 1: New actor detected → express surprise and greet
    if (Delta.AddedCount > 0)
    {
        const FSarembokActorDelta* AddedActor = nullptr;
        for (const FSarembokActorDelta& D : Delta.Deltas)
        {
            if (D.DeltaType == ESarembokDeltaType::ActorAdded)
            {
                AddedActor = &D;
                break;
            }
        }

        if (AddedActor)
        {
            Intent.bShouldAct = true;
            Intent.ActionType = TEXT("Speak");
            Intent.Target = TEXT("Avatar");
            Intent.EmotionState = TEXT("Surprised");
            Intent.SpeechText = FString::Printf(
                TEXT("I notice something new: %s"),
                *AddedActor->Actor.ActorName
            );
            Intent.Reason = FString::Printf(
                TEXT("New actor detected: %s (type: %s)"),
                *AddedActor->Actor.ActorName,
                *AddedActor->Actor.ActorType
            );
            return Intent;
        }
    }

    // Rule 2: Actor departed → express sadness
    if (Delta.RemovedCount > 0)
    {
        const FSarembokActorDelta* RemovedActor = nullptr;
        for (const FSarembokActorDelta& D : Delta.Deltas)
        {
            if (D.DeltaType == ESarembokDeltaType::ActorRemoved)
            {
                RemovedActor = &D;
                break;
            }
        }

        if (RemovedActor)
        {
            Intent.bShouldAct = true;
            Intent.ActionType = TEXT("Emotion");
            Intent.Target = TEXT("Avatar");
            Intent.EmotionState = TEXT("Sad");
            Intent.Reason = FString::Printf(
                TEXT("Actor departed: %s"),
                *RemovedActor->Actor.ActorName
            );
            return Intent;
        }
    }

    // Rule 3: Actor moved significantly → express interest
    if (Delta.MovedCount > 0)
    {
        Intent.bShouldAct = true;
        Intent.ActionType = TEXT("Emotion");
        Intent.Target = TEXT("Avatar");
        Intent.EmotionState = TEXT("Happy");
        Intent.Reason = FString::Printf(
            TEXT("Movement detected: %d actor(s) moved"),
            Delta.MovedCount
        );
        return Intent;
    }

    // Rule 4: Extended idle (no changes for N cycles) → calm expression
    if (IdleCycles > 3 && !Delta.bHasChanges)
    {
        Intent.bShouldAct = true;
        Intent.ActionType = TEXT("Emotion");
        Intent.Target = TEXT("Avatar");
        Intent.EmotionState = TEXT("Calm");
        Intent.Reason = FString::Printf(
            TEXT("Scene stable for %d cycles"),
            IdleCycles
        );
        return Intent;
    }

    // No action needed
    Intent.bShouldAct = false;
    Intent.Reason = TEXT("No significant changes detected");
    return Intent;
}
