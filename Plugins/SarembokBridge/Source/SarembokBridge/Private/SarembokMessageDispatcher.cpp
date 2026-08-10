#include "SarembokMessageDispatcher.h"

#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "SarembokAvatarComponent.h"
#include "SarembokAvatarController.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Containers/Ticker.h"

FSarembokMessageDispatcher::FSarembokMessageDispatcher()
{
    QueueTickerHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateRaw(this, &FSarembokMessageDispatcher::ProcessQueuedCommands),
        0.1f
    );
}

FSarembokMessageDispatcher::~FSarembokMessageDispatcher()
{
    if (QueueTickerHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(QueueTickerHandle);
        QueueTickerHandle.Reset();
    }
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

    if (!ExecuteCommand(Message))
    {
        PendingCommands.Add(Message);

        UE_LOG(
            LogTemp,
            Display,
            TEXT("[SAREMBOK] COMMAND QUEUED | Command=%s | Pending=%d | Waiting for game world/avatar"),
            *LastCommand,
            PendingCommands.Num()
        );
    }
}

bool FSarembokMessageDispatcher::ExecuteCommand(const FString& Message)
{
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
        return false;
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

        if (!AvatarController)
        {
            return false;
        }

        if (Emotion.IsEmpty())
        {
            UE_LOG(
                LogTemp,
                Warning,
                TEXT("[SAREMBOK] Emotion command missing state payload")
            );
            return true;
        }

        AvatarController->SetEmotion(Emotion);

        UE_LOG(
            LogTemp,
            Display,
            TEXT("[SAREMBOK] AVATAR EMOTION EXECUTED | %s"),
            *Emotion
        );

        return true;
    }

    if (LastCommand.Equals(TEXT("Speak"), ESearchCase::IgnoreCase))
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

        if (!AvatarComponent)
        {
            return false;
        }

        if (Text.IsEmpty())
        {
            UE_LOG(
                LogTemp,
                Warning,
                TEXT("[SAREMBOK] Speak command missing text payload")
            );
            return true;
        }

        if (AvatarController && !Emotion.IsEmpty())
        {
            AvatarController->SetEmotion(Emotion);
        }

        AvatarComponent->Speak(Text);

        UE_LOG(
            LogTemp,
            Display,
            TEXT("[SAREMBOK] AVATAR SPEECH EXECUTED | %s"),
            *Text
        );

        return true;
    }

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] Command received with no Avatar executor: %s"),
        *LastCommand
    );

    return true;
}

bool FSarembokMessageDispatcher::ProcessQueuedCommands(float DeltaTime)
{
    if (PendingCommands.IsEmpty())
    {
        return true;
    }

    TArray<FString> CommandsToProcess = MoveTemp(PendingCommands);

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK] COMMAND QUEUE CHECK | Pending=%d"),
        CommandsToProcess.Num()
    );

    for (const FString& Message : CommandsToProcess)
    {
        ParseCommand(Message);

        if (LastCommand.IsEmpty())
        {
            continue;
        }

        if (!ExecuteCommand(Message))
        {
            PendingCommands.Add(Message);
        }
    }

    if (!PendingCommands.IsEmpty())
    {
        UE_LOG(
            LogTemp,
            Display,
            TEXT("[SAREMBOK] COMMAND QUEUE WAITING | Pending=%d"),
            PendingCommands.Num()
        );
    }

    return true;
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
