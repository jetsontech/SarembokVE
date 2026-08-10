#include "SarembokDeterministicReasoner.h"

FSarembokIntent FSarembokDeterministicReasoner::ReasonWithGoal(
    const FSarembokWorldDelta& Delta,
    const FSarembokGoal& ActiveGoal,
    const TArray<FSarembokEpisode>& RecentEpisodes,
    int32 IdleCycles)
{
    FSarembokIntent Intent;
    Intent.GoalId = ActiveGoal.GoalId;
    Intent.PlanId = FString::Printf(TEXT("plan-%s"), *ActiveGoal.GoalId.Left(8));

    // Rule 0: Initial perception scan (first cycle ever)
    if (RecentEpisodes.Num() == 0)
    {
        Intent.bShouldAct = true;
        Intent.ActionType = TEXT("Emotion");
        Intent.Target = TEXT("Avatar");
        Intent.EmotionState = TEXT("Calm");
        Intent.Confidence = 1.0f;
        Intent.Reason = TEXT("Initial autonomous perception scan");
        Intent.AlternativeActions.Add(TEXT("Observe"));
        Intent.AlternativeActions.Add(TEXT("Wait"));
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
            Intent.Confidence = 0.95f;
            Intent.Reason = FString::Printf(
                TEXT("New actor detected: %s (type: %s)"),
                *AddedActor->Actor.ActorName,
                *AddedActor->Actor.ActorType
            );
            Intent.AlternativeActions.Add(TEXT("Emotion:Surprised"));
            Intent.AlternativeActions.Add(TEXT("Observe"));
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
            Intent.Confidence = 0.90f;
            Intent.Reason = FString::Printf(
                TEXT("Actor departed: %s"),
                *RemovedActor->Actor.ActorName
            );
            Intent.AlternativeActions.Add(TEXT("Speak:Goodbye"));
            Intent.AlternativeActions.Add(TEXT("Wait"));
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
        Intent.Confidence = 0.85f;
        Intent.Reason = FString::Printf(
            TEXT("Movement detected: %d actor(s) moved"),
            Delta.MovedCount
        );
        Intent.AlternativeActions.Add(TEXT("Observe"));
        return Intent;
    }

    // Rule 4: Active Goal pursuing (if explicitly set)
    if (!ActiveGoal.GoalId.IsEmpty() && ActiveGoal.Status.Equals(TEXT("Active"), ESearchCase::IgnoreCase))
    {
        Intent.bShouldAct = true;
        Intent.ActionType = TEXT("Speak");
        Intent.Target = TEXT("Avatar");
        Intent.EmotionState = TEXT("Joyful");
        Intent.SpeechText = FString::Printf(TEXT("Pursuing active goal: %s"), *ActiveGoal.Description);
        Intent.Confidence = 0.92f;
        Intent.Reason = FString::Printf(TEXT("Executing active goal [%s]"), *ActiveGoal.GoalId);
        Intent.AlternativeActions.Add(TEXT("Emotion:Joyful"));
        return Intent;
    }

    // Rule 5: Extended idle (no changes for N cycles) → calm expression
    if (IdleCycles > 3 && !Delta.bHasChanges)
    {
        Intent.bShouldAct = true;
        Intent.ActionType = TEXT("Emotion");
        Intent.Target = TEXT("Avatar");
        Intent.EmotionState = TEXT("Calm");
        Intent.Confidence = 0.75f;
        Intent.Reason = FString::Printf(
            TEXT("Scene stable for %d cycles"),
            IdleCycles
        );
        Intent.AlternativeActions.Add(TEXT("Wait"));
        return Intent;
    }

    // No action needed
    Intent.bShouldAct = false;
    Intent.Confidence = 0.50f;
    Intent.Reason = TEXT("No significant changes detected");
    return Intent;
}

FSarembokIntent FSarembokDeterministicReasoner::Reason(
    const FSarembokWorldDelta& Delta,
    const TArray<FSarembokEpisode>& RecentEpisodes,
    int32 IdleCycles)
{
    FSarembokGoal DummyGoal;
    return ReasonWithGoal(Delta, DummyGoal, RecentEpisodes, IdleCycles);
}
