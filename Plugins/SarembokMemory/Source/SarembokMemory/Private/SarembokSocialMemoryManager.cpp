// ============================================================
// SarembokSocialMemoryManager.cpp
// Persistent Identity & Social Memory Subsystem Implementation
// ============================================================

#include "SarembokSocialMemoryManager.h"

void USarembokSocialMemoryManager::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    Profiles.Empty();

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][SOCIAL_MEMORY] INITIALIZED"));
}

void USarembokSocialMemoryManager::Deinitialize()
{
    Profiles.Empty();
    Super::Deinitialize();
}

FSarembokSocialProfile USarembokSocialMemoryManager::GetOrCreateProfile(const FString& UserId, const FString& DisplayName)
{
    if (Profiles.Contains(UserId))
    {
        FSarembokSocialProfile& Profile = Profiles[UserId];
        Profile.LastSeen = FDateTime::UtcNow();
        Profile.InteractionCount++;
        Profile.FamiliarityScore = FMath::Min(1.0f, Profile.FamiliarityScore + 0.15f);

        UE_LOG(LogTemp, Display,
            TEXT("[SAREMBOK][SOCIAL_MEMORY] RECOGNIZED | UserId=%s | Name=%s | Interactions=%d | Familiarity=%.2f"),
            *Profile.UserId, *Profile.DisplayName, Profile.InteractionCount, Profile.FamiliarityScore);

        return Profile;
    }

    FSarembokSocialProfile NewProfile;
    NewProfile.UserId = UserId;
    NewProfile.DisplayName = DisplayName;
    NewProfile.FirstSeen = FDateTime::UtcNow();
    NewProfile.LastSeen = FDateTime::UtcNow();
    NewProfile.InteractionCount = 1;
    NewProfile.RelationshipState = TEXT("Acquaintance");
    NewProfile.TrustScore = 0.5f;
    NewProfile.FamiliarityScore = 0.1f;

    Profiles.Add(UserId, NewProfile);

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][SOCIAL_MEMORY] PROFILE_CREATED | UserId=%s | Name=%s"),
        *NewProfile.UserId, *NewProfile.DisplayName);

    return NewProfile;
}

bool USarembokSocialMemoryManager::GetProfile(const FString& UserId, FSarembokSocialProfile& OutProfile) const
{
    if (const FSarembokSocialProfile* Found = Profiles.Find(UserId))
    {
        OutProfile = *Found;
        return true;
    }
    return false;
}

void USarembokSocialMemoryManager::UpdateFact(const FString& UserId, const FString& Key, const FString& Value)
{
    if (FSarembokSocialProfile* Profile = Profiles.Find(UserId))
    {
        Profile->KnownFacts.Add(Key, Value);

        UE_LOG(LogTemp, Display,
            TEXT("[SAREMBOK][SOCIAL_MEMORY] FACT_UPDATED | UserId=%s | Key=%s | Value=%s"),
            *UserId, *Key, *Value);
    }
}

bool USarembokSocialMemoryManager::DetectFactContradiction(const FString& UserId, const FString& Key, const FString& NewValue, FString& OutExistingValue)
{
    if (FSarembokSocialProfile* Profile = Profiles.Find(UserId))
    {
        if (const FString* Existing = Profile->KnownFacts.Find(Key))
        {
            if (!Existing->Equals(NewValue, ESearchCase::IgnoreCase))
            {
                OutExistingValue = *Existing;

                UE_LOG(LogTemp, Warning,
                    TEXT("[SAREMBOK][SOCIAL_MEMORY] CONTRADICTION_DETECTED | UserId=%s | Key=%s | Stored=%s | Claimed=%s"),
                    *UserId, *Key, **Existing, *NewValue);

                return true;
            }
        }
    }
    return false;
}

void USarembokSocialMemoryManager::RecordInteraction(const FString& UserId, const FString& ConversationId, const FString& Topic)
{
    if (FSarembokSocialProfile* Profile = Profiles.Find(UserId))
    {
        Profile->LastConversationId = ConversationId;
        if (!Topic.IsEmpty())
        {
            Profile->RecentTopics.Add(Topic);
            if (!Profile->PreferredTopics.Contains(Topic))
            {
                Profile->PreferredTopics.Add(Topic);
            }
        }

        UE_LOG(LogTemp, Display,
            TEXT("[SAREMBOK][SOCIAL_MEMORY] INTERACTION_RECORDED | UserId=%s | ConvId=%s | Topic=%s"),
            *UserId, *ConversationId, *Topic);
    }
}

int32 USarembokSocialMemoryManager::GetTotalProfiles() const
{
    return Profiles.Num();
}
