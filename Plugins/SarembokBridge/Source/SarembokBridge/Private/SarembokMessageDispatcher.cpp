#include "SarembokMessageDispatcher.h"

#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "SarembokAvatarComponent.h"
#include "SarembokAvatarController.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

FSarembokMessageDispatcher::FSarembokMessageDispatcher()
{
}

FSarembokMessageDispatcher::~FSarembokMessageDispatcher()
{
}

void FSarembokMessageDispatcher::DispatchMessage(const FString& Message)
{
    ParseCommand(Message);

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] COMMAND ROUTED | Command=%s | Target=%s | Payload=%s"),
        *LastCommand,
        *LastTarget,
        *LastPayload
    );

    if (LastCommand.IsEmpty())
    {
        return;
    }

    UWorld* RuntimeWorld = nullptr;

    if (GEngine)
    {
        for (const FWorldContext& Context : GEngine->GetWorldContexts())
        {
            if (Context.WorldType == EWorldType::Game ||
                Context.WorldType == EWorldType::PIE)
            {
                RuntimeWorld = Context.World();
                if (RuntimeWorld)
                {
                    break;
                }
            }
        }
    }

    if (!RuntimeWorld)
    {
        UE_LOG(
            LogTemp,
            Warning,
            TEXT("[SAREMBOK] Command queued but no game world is available yet")
        );
        return;
    }

    USarembokAvatarComponent* AvatarComponent = nullptr;
    USarembokAvatarController* AvatarController = nullptr;

    for (TActorIterator<AActor> It(RuntimeWorld); It; ++It)
    {
        if (!AvatarComponent)
        {
            AvatarComponent = It->FindComponentByClass<USarembokAvatarComponent>();
        }

        if (!AvatarController)
        {
            AvatarController = It->FindComponentByClass<USarembokAvatarController>();
        }

        if (AvatarComponent && AvatarController)
        {
            break;
        }
    }

    if (LastCommand.Equals(TEXT("Emotion"), ESearchCase::IgnoreCase))
    {
        FString Emotion;

        TSharedPtr<FJsonObject> JsonObject;
        TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);

        if (FJsonSerializer::Deserialize(Reader, JsonObject) && JsonObject.IsValid())
        {
            const TSharedPtr<FJsonObject>* PayloadObject = nullptr;

            if (JsonObject->TryGetObjectField(TEXT("payload"), PayloadObject) &&
                PayloadObject &&
                PayloadObject->IsValid())
            {
                (*PayloadObject)->TryGetStringField(TEXT("state"), Emotion);
            }
        }

        if (AvatarController && !Emotion.IsEmpty())
        {
            AvatarController->SetEmotion(Emotion);

            UE_LOG(
                LogTemp,
                Display,
                TEXT("[SAREMBOK] AVATAR EMOTION EXECUTED | %s"),
                *Emotion
            );
        }
        else
        {
            UE_LOG(
                LogTemp,
                Warning,
                TEXT("[SAREMBOK] Emotion command could not find an AvatarController")
            );
        }
    }
    else if (LastCommand.Equals(TEXT("Speak"), ESearchCase::IgnoreCase))
    {
        FString Text;
        FString Emotion;

        TSharedPtr<FJsonObject> JsonObject;
        TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);

        if (FJsonSerializer::Deserialize(Reader, JsonObject) && JsonObject.IsValid())
        {
            const TSharedPtr<FJsonObject>* PayloadObject = nullptr;

            if (JsonObject->TryGetObjectField(TEXT("payload"), PayloadObject) &&
                PayloadObject &&
                PayloadObject->IsValid())
            {
                (*PayloadObject)->TryGetStringField(TEXT("text"), Text);
                (*PayloadObject)->TryGetStringField(TEXT("emotion"), Emotion);
            }
        }

        if (AvatarController && !Emotion.IsEmpty())
        {
            AvatarController->SetEmotion(Emotion);
        }

        if (AvatarComponent && !Text.IsEmpty())
        {
            AvatarComponent->Speak(Text);

            UE_LOG(
                LogTemp,
                Display,
                TEXT("[SAREMBOK] AVATAR SPEECH EXECUTED | %s"),
                *Text
            );
        }
        else
        {
            UE_LOG(
                LogTemp,
                Warning,
                TEXT("[SAREMBOK] Speak command could not find a SarembokAvatarComponent or text payload")
            );
        }
    }
    else
    {
        UE_LOG(
            LogTemp,
            Display,
            TEXT("[SAREMBOK] Command received with no Avatar executor: %s"),
            *LastCommand
        );
    }
}

void FSarembokMessageDispatcher::ParseCommand(const FString& Message)
{
    LastCommand.Empty();
    LastTarget.Empty();
    LastPayload.Empty();

    TSharedPtr<FJsonObject> JsonObject;

    TSharedRef<TJsonReader<>> Reader =
        TJsonReaderFactory<>::Create(Message);

    if (!FJsonSerializer::Deserialize(Reader, JsonObject) ||
        !JsonObject.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("[SAREMBOK] Invalid command JSON"));
        return;
    }

    JsonObject->TryGetStringField(TEXT("command"), LastCommand);
    JsonObject->TryGetStringField(TEXT("target"), LastTarget);

    const TSharedPtr<FJsonObject>* PayloadObject = nullptr;

    if (JsonObject->TryGetObjectField(TEXT("payload"), PayloadObject) &&
        PayloadObject &&
        PayloadObject->IsValid())
    {
        TSharedRef<TJsonWriter<>> Writer =
            TJsonWriterFactory<>::Create(&LastPayload);

        FJsonSerializer::Serialize(PayloadObject->ToSharedRef(), Writer);
        Writer->Close();
    }

    if (LastCommand.IsEmpty())
    {
        UE_LOG(LogTemp, Warning, TEXT("[SAREMBOK] Command received without command field"));
    }
}

FString FSarembokMessageDispatcher::GetLastCommand() const
{
    return LastCommand;
}
