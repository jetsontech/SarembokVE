// ============================================================
// SarembokEventReplayEngine.h
// Event Replay & Authoritative Social State Reconstruction Engine
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokSocialProfile.h"
#include "SarembokEventReplayEngine.generated.h"

UCLASS()
class SAREMBOKMEMORY_API USarembokEventReplayEngine : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category = "Sarembok|EventReplay")
    bool ReconstructSocialProfileFromEvents(const FString& UserId, const TArray<FString>& EventJsons, FSarembokSocialProfile& OutReconstructedProfile);

    UFUNCTION(BlueprintPure, Category = "Sarembok|EventReplay")
    int32 GetReplayedEventCount() const;

private:

    int32 ReplayedCount = 0;
};
