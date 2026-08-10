// ============================================================
// SarembokConversationManager.cpp
// ============================================================

#include "SarembokConversationManager.h"

void USarembokConversationManager::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    ResetConversation();

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Conversation Manager Subsystem Initialized"));
}

void USarembokConversationManager::Deinitialize()
{
    Super::Deinitialize();
}

void USarembokConversationManager::ResetConversation()
{
    State = FSarembokConversationalState();
    State.ConversationId = FString::Printf(TEXT("conv-%06d"), FMath::RandRange(1000, 9999));
    State.TurnId = 0;
    State.UserState.bPresent = true;
    State.UserState.Distance = 150.0f;
    State.IntentType = TEXT("greeting");
    State.IntentConfidence = 0.95f;
    State.RecentTopics.Empty();
    State.RecentTopics.Add(TEXT("AI Workstation"));
}

void USarembokConversationManager::ProcessUserTurn(const FString& UserSpeech)
{
    State.TurnId++;

    if (UserSpeech.Contains(TEXT("workstation"), ESearchCase::IgnoreCase) ||
        UserSpeech.Contains(TEXT("equipment"), ESearchCase::IgnoreCase))
    {
        State.IntentType = TEXT("query_equipment");
        State.RecentTopics.AddUnique(TEXT("Equipment Location"));
    }
    else if (UserSpeech.Contains(TEXT("help"), ESearchCase::IgnoreCase) ||
             UserSpeech.Contains(TEXT("question"), ESearchCase::IgnoreCase))
    {
        State.IntentType = TEXT("request_help");
        State.RecentTopics.AddUnique(TEXT("Assistance"));
    }
    else
    {
        State.IntentType = TEXT("general_dialog");
        State.RecentTopics.AddUnique(TEXT("General Topic"));
    }

    State.IntentConfidence = 0.96f;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][CONVERSATION] TURN TurnId=%d Intent=%s Topic=%s Speech=%s"),
        State.TurnId,
        *State.IntentType,
        *State.RecentTopics.Last(),
        *UserSpeech
    );

    OnConversationTurn.Broadcast(State.TurnId, UserSpeech);
}

void USarembokConversationManager::UpdateUserPresence(bool bPresent, float Distance)
{
    State.UserState.bPresent = bPresent;
    State.UserState.Distance = Distance;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][CONVERSATION] USER_PRESENCE Present=%s Dist=%.1f"),
        bPresent ? TEXT("true") : TEXT("false"),
        Distance
    );
}

const FSarembokConversationalState& USarembokConversationManager::GetConversationalState() const
{
    return State;
}
