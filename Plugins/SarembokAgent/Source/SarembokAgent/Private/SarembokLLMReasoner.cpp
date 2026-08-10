#include "SarembokLLMReasoner.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonWriter.h"
#include "Serialization/JsonSerializer.h"

FSarembokLLMReasoner::FSarembokLLMReasoner(bool bEnableAI, const FString& Endpoint)
    : bAIOnline(bEnableAI)
    , ServerEndpoint(Endpoint)
{
}

FString FSarembokLLMReasoner::FormatLLMPrompt(
    const FSarembokWorldDelta& Delta,
    const FSarembokGoal& ActiveGoal,
    const TArray<FSarembokEpisode>& RecentEpisodes) const
{
    TSharedPtr<FJsonObject> PromptObj = MakeShared<FJsonObject>();

    PromptObj->SetStringField(TEXT("goal_id"), ActiveGoal.GoalId);
    PromptObj->SetStringField(TEXT("goal_desc"), ActiveGoal.Description);
    PromptObj->SetNumberField(TEXT("goal_priority"), ActiveGoal.Priority);

    PromptObj->SetNumberField(TEXT("delta_added"), Delta.AddedCount);
    PromptObj->SetNumberField(TEXT("delta_removed"), Delta.RemovedCount);
    PromptObj->SetNumberField(TEXT("delta_moved"), Delta.MovedCount);

    PromptObj->SetNumberField(TEXT("recent_episodes"), RecentEpisodes.Num());

    FString OutputString;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);
    FJsonSerializer::Serialize(PromptObj.ToSharedRef(), Writer);
    return OutputString;
}

FSarembokIntent FSarembokLLMReasoner::ReasonWithGoal(
    const FSarembokWorldDelta& Delta,
    const FSarembokGoal& ActiveGoal,
    const TArray<FSarembokEpisode>& RecentEpisodes,
    int32 IdleCycles)
{
    if (!bAIOnline)
    {
        UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][AGENT] LLM_PROVIDER_UNAVAILABLE"));
        UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][AGENT] FALLBACK_DETERMINISTIC"));
        UE_LOG(LogTemp, Display,
            TEXT("[SAREMBOK][AGENT] LLM_FALLBACK_ACTIVE | Provider=LLMReasoner | Fallback=DeterministicReasoner"));

        FSarembokIntent Intent = FallbackReasoner.ReasonWithGoal(Delta, ActiveGoal, RecentEpisodes, IdleCycles);
        Intent.Reason = FString::Printf(TEXT("[LLM-Fallback] %s"), *Intent.Reason);
        return Intent;
    }

    // AI Online Mode: Formulate structured prompt
    FString PromptJson = FormatLLMPrompt(Delta, ActiveGoal, RecentEpisodes);

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][AGENT] LLM_REASONING_PROMPT | Endpoint=%s | Prompt=%s"),
        *ServerEndpoint, *PromptJson);

    // AI Response Simulation / Endpoint Hook
    FSarembokIntent Intent;
    Intent.bShouldAct = true;
    Intent.ActionType = TEXT("Speak");
    Intent.Target = TEXT("Avatar");
    Intent.EmotionState = TEXT("Joyful");
    Intent.SpeechText = TEXT("AI core reasoning generated response.");
    Intent.Confidence = 0.98f;
    Intent.GoalId = ActiveGoal.GoalId;
    Intent.Reason = TEXT("External LLM provider decision.");
    Intent.AlternativeActions.Add(TEXT("Emotion:Calm"));

    return Intent;
}
