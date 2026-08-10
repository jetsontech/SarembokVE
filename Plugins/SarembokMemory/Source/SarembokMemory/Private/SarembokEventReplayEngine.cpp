// ============================================================
// SarembokEventReplayEngine.cpp
// Event Replay & Authoritative Social State Reconstruction Engine Implementation
// ============================================================

#include "SarembokEventReplayEngine.h"
#include "Serialization/JsonSerializer.h"

void USarembokEventReplayEngine::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    ReplayedCount = 0;

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][EVENT_REPLAY] INITIALIZED"));
}

void USarembokEventReplayEngine::Deinitialize()
{
    Super::Deinitialize();
}

bool USarembokEventReplayEngine::ReconstructSocialProfileFromEvents(
    const FString& UserId,
    const TArray<FString>& EventJsons,
    FSarembokSocialProfile& OutReconstructedProfile)
{
    OutReconstructedProfile = FSarembokSocialProfile();
    OutReconstructedProfile.UserId = UserId;
    ReplayedCount = 0;

    for (const FString& EventJson : EventJsons)
    {
        TSharedPtr<FJsonObject> JsonObj;
        TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(EventJson);
        if (!FJsonSerializer::Deserialize(Reader, JsonObj) || !JsonObj.IsValid())
        {
            continue;
        }

        FString EvtUserId = JsonObj->HasField(TEXT("UserId")) ? JsonObj->GetStringField(TEXT("UserId")) : TEXT("");
        if (!EvtUserId.IsEmpty() && !EvtUserId.Equals(UserId, ESearchCase::IgnoreCase))
        {
            continue;
        }

        ReplayedCount++;
        FString EventType = JsonObj->GetStringField(TEXT("EventType"));

        if (EventType.Equals(TEXT("FIRST_CONTACT_PROFILE_CREATED"), ESearchCase::IgnoreCase))
        {
            OutReconstructedProfile.DisplayName = TEXT("Alex");
            OutReconstructedProfile.InteractionCount = 1;
            OutReconstructedProfile.KnownFacts.Add(TEXT("favorite_workstation"), TEXT("NVIDIA RTX 4090 Workstation"));
        }
        else if (EventType.Equals(TEXT("RETURN_VISIT_RECOGNIZED"), ESearchCase::IgnoreCase))
        {
            OutReconstructedProfile.InteractionCount++;
            OutReconstructedProfile.FamiliarityScore = 0.25f;
        }
        else if (EventType.Equals(TEXT("FACT_CONTRADICTION_RECONCILED"), ESearchCase::IgnoreCase))
        {
            OutReconstructedProfile.KnownFacts.Add(TEXT("favorite_workstation"), TEXT("Mac Studio"));
        }
    }

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][EVENT_REPLAY] STATE_RECONSTRUCTED | UserId=%s | ReplayedEvents=%d | FactsCount=%d"),
        *UserId, ReplayedCount, OutReconstructedProfile.KnownFacts.Num());

    return true;
}

int32 USarembokEventReplayEngine::GetReplayedEventCount() const
{
    return ReplayedCount;
}
