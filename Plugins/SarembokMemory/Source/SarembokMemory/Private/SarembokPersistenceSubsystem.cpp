// ============================================================
// SarembokPersistenceSubsystem.cpp
// Crash-Safe Disk Persistence Engine Implementation
// ============================================================

#include "SarembokPersistenceSubsystem.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"

void USarembokPersistenceSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    PersistenceDirectory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("SarembokPersistence"));
    InitializeDatabase();

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PERSISTENCE] INITIALIZED | Dir=%s"), *PersistenceDirectory);
}

void USarembokPersistenceSubsystem::Deinitialize()
{
    Super::Deinitialize();
}

bool USarembokPersistenceSubsystem::InitializeDatabase()
{
    IFileManager::Get().MakeDirectory(*PersistenceDirectory, true);
    FString VersionFile = FPaths::Combine(PersistenceDirectory, TEXT("schema_version.txt"));
    FFileHelper::SaveStringToFile(SchemaVersion, *VersionFile);

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PERSISTENCE] DB_INITIALIZED | Schema=%s"), *SchemaVersion);
    return true;
}

bool USarembokPersistenceSubsystem::SaveSocialProfile(const FSarembokSocialProfile& Profile)
{
    if (Profile.UserId.IsEmpty())
    {
        return false;
    }

    FString ProfilePath = FPaths::Combine(PersistenceDirectory, FString::Printf(TEXT("profile_%s.json"), *Profile.UserId));

    TSharedRef<FJsonObject> JsonObj = MakeShared<FJsonObject>();
    JsonObj->SetStringField(TEXT("UserId"), Profile.UserId);
    JsonObj->SetStringField(TEXT("DisplayName"), Profile.DisplayName);
    JsonObj->SetNumberField(TEXT("InteractionCount"), Profile.InteractionCount);
    JsonObj->SetNumberField(TEXT("TrustScore"), Profile.TrustScore);
    JsonObj->SetNumberField(TEXT("FamiliarityScore"), Profile.FamiliarityScore);
    JsonObj->SetStringField(TEXT("RelationshipState"), Profile.RelationshipState);

    TSharedRef<FJsonObject> FactsObj = MakeShared<FJsonObject>();
    for (const auto& KVP : Profile.KnownFacts)
    {
        FactsObj->SetStringField(KVP.Key, KVP.Value);
    }
    JsonObj->SetObjectField(TEXT("KnownFacts"), FactsObj);

    FString OutputJson;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputJson);
    FJsonSerializer::Serialize(JsonObj, Writer);

    bool bSaved = FFileHelper::SaveStringToFile(OutputJson, *ProfilePath);
    if (bSaved)
    {
        UE_LOG(LogTemp, Display,
            TEXT("[SAREMBOK][PERSISTENCE] PROFILE_SAVED | UserId=%s | Path=%s"),
            *Profile.UserId, *ProfilePath);
    }
    return bSaved;
}

bool USarembokPersistenceSubsystem::LoadSocialProfile(const FString& UserId, FSarembokSocialProfile& OutProfile)
{
    FString ProfilePath = FPaths::Combine(PersistenceDirectory, FString::Printf(TEXT("profile_%s.json"), *UserId));
    if (!FPaths::FileExists(ProfilePath))
    {
        return false;
    }

    FString JsonString;
    if (!FFileHelper::LoadFileToString(JsonString, *ProfilePath))
    {
        return false;
    }

    TSharedPtr<FJsonObject> JsonObj;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonString);
    if (!FJsonSerializer::Deserialize(Reader, JsonObj) || !JsonObj.IsValid())
    {
        return false;
    }

    OutProfile.UserId = JsonObj->GetStringField(TEXT("UserId"));
    OutProfile.DisplayName = JsonObj->GetStringField(TEXT("DisplayName"));
    OutProfile.InteractionCount = JsonObj->GetIntegerField(TEXT("InteractionCount"));
    OutProfile.TrustScore = JsonObj->GetNumberField(TEXT("TrustScore"));
    OutProfile.FamiliarityScore = JsonObj->GetNumberField(TEXT("FamiliarityScore"));
    OutProfile.RelationshipState = JsonObj->GetStringField(TEXT("RelationshipState"));

    const TSharedPtr<FJsonObject>* FactsObj;
    if (JsonObj->TryGetObjectField(TEXT("KnownFacts"), FactsObj))
    {
        OutProfile.KnownFacts.Empty();
        for (const auto& KVP : (*FactsObj)->Values)
        {
            OutProfile.KnownFacts.Add(FString(KVP.Key), KVP.Value->AsString());
        }
    }

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][PERSISTENCE] PROFILE_LOADED | UserId=%s | Interactions=%d | Familiarity=%.2f"),
        *OutProfile.UserId, OutProfile.InteractionCount, OutProfile.FamiliarityScore);

    return true;
}

bool USarembokPersistenceSubsystem::SaveEventJson(const FString& EventId, const FString& EventJson)
{
    FString EventsDir = FPaths::Combine(PersistenceDirectory, TEXT("Events"));
    IFileManager::Get().MakeDirectory(*EventsDir, true);
    FString EventPath = FPaths::Combine(EventsDir, FString::Printf(TEXT("%s.json"), *EventId));

    bool bSaved = FFileHelper::SaveStringToFile(EventJson, *EventPath);
    if (bSaved)
    {
        UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PERSISTENCE] EVENT_SAVED | EventId=%s"), *EventId);
    }
    return bSaved;
}

int32 USarembokPersistenceSubsystem::LoadAllEventsJson(TArray<FString>& OutEventJsons)
{
    OutEventJsons.Empty();
    FString EventsDir = FPaths::Combine(PersistenceDirectory, TEXT("Events"));
    TArray<FString> EventFiles;
    IFileManager::Get().FindFiles(EventFiles, *EventsDir, TEXT("*.json"));

    for (const FString& File : EventFiles)
    {
        FString FullPath = FPaths::Combine(EventsDir, File);
        FString Content;
        if (FFileHelper::LoadFileToString(Content, *FullPath))
        {
            OutEventJsons.Add(Content);
        }
    }

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][PERSISTENCE] EVENTS_LOADED Count=%d"), OutEventJsons.Num());
    return OutEventJsons.Num();
}

FString USarembokPersistenceSubsystem::GetSchemaVersion() const
{
    return SchemaVersion;
}
