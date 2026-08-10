// ============================================================
// SarembokSocialProfile.h
// Persistent Identity & Social Memory Profile Schema
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "SarembokSocialProfile.generated.h"

/**
 * Persistent Social Profile representing individual-level identity,
 * interaction history, preferences, and facts across conversations.
 */
USTRUCT(BlueprintType)
struct SAREMBOKMEMORY_API FSarembokSocialProfile
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|SocialMemory")
    FString UserId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|SocialMemory")
    FString DisplayName;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|SocialMemory")
    FDateTime FirstSeen;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|SocialMemory")
    FDateTime LastSeen;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|SocialMemory")
    int32 InteractionCount = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|SocialMemory")
    TArray<FString> PreferredTopics;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|SocialMemory")
    TMap<FString, FString> KnownFacts;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|SocialMemory")
    TArray<FString> RecentTopics;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|SocialMemory")
    FString RelationshipState = TEXT("Acquaintance"); // "Acquaintance", "Collaborator", "Trusted"

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|SocialMemory")
    float TrustScore = 0.5f; // 0.0 to 1.0

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|SocialMemory")
    float FamiliarityScore = 0.1f; // 0.0 to 1.0

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok|SocialMemory")
    FString LastConversationId;

    FSarembokSocialProfile()
        : FirstSeen(FDateTime::UtcNow())
        , LastSeen(FDateTime::UtcNow())
    {
    }
};
