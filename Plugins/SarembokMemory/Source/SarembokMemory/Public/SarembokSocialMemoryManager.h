// ============================================================
// SarembokSocialMemoryManager.h
// Persistent Identity & Social Memory Subsystem
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokSocialProfile.h"
#include "SarembokSocialMemoryManager.generated.h"

UCLASS()
class SAREMBOKMEMORY_API USarembokSocialMemoryManager : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category = "Sarembok|SocialMemory")
    FSarembokSocialProfile GetOrCreateProfile(const FString& UserId, const FString& DisplayName);

    UFUNCTION(BlueprintPure, Category = "Sarembok|SocialMemory")
    bool GetProfile(const FString& UserId, FSarembokSocialProfile& OutProfile) const;

    UFUNCTION(BlueprintCallable, Category = "Sarembok|SocialMemory")
    void UpdateFact(const FString& UserId, const FString& Key, const FString& Value);

    UFUNCTION(BlueprintCallable, Category = "Sarembok|SocialMemory")
    bool DetectFactContradiction(const FString& UserId, const FString& Key, const FString& NewValue, FString& OutExistingValue);

    UFUNCTION(BlueprintCallable, Category = "Sarembok|SocialMemory")
    void RecordInteraction(const FString& UserId, const FString& ConversationId, const FString& Topic);

    UFUNCTION(BlueprintPure, Category = "Sarembok|SocialMemory")
    int32 GetTotalProfiles() const;

private:

    UPROPERTY()
    TMap<FString, FSarembokSocialProfile> Profiles;
};
