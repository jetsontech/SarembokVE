// ============================================================
// SarembokPersistenceSubsystem.h
// Crash-Safe Disk Persistence & Database Subsystem
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokSocialProfile.h"
#include "SarembokPersistenceSubsystem.generated.h"

UCLASS()
class SAREMBOKMEMORY_API USarembokPersistenceSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category = "Sarembok|Persistence")
    bool InitializeDatabase();

    UFUNCTION(BlueprintCallable, Category = "Sarembok|Persistence")
    bool SaveSocialProfile(const FSarembokSocialProfile& Profile);

    UFUNCTION(BlueprintCallable, Category = "Sarembok|Persistence")
    bool LoadSocialProfile(const FString& UserId, FSarembokSocialProfile& OutProfile);

    UFUNCTION(BlueprintCallable, Category = "Sarembok|Persistence")
    bool SaveEventJson(const FString& EventId, const FString& EventJson);

    UFUNCTION(BlueprintCallable, Category = "Sarembok|Persistence")
    int32 LoadAllEventsJson(TArray<FString>& OutEventJsons);

    UFUNCTION(BlueprintPure, Category = "Sarembok|Persistence")
    FString GetSchemaVersion() const;

private:

    FString PersistenceDirectory;
    FString SchemaVersion = TEXT("v1.7_init_schema");
};
