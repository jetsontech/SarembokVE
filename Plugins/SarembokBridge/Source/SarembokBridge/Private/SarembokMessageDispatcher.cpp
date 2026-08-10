#include "SarembokMessageDispatcher.h"
#include "SarembokCommandConstants.h"

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
        FTickerDelegate::CreateRaw(
            this,
            &FSarembokMessageDispatcher::ProcessQueuedCommands
        ),
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
        TEXT("[SAREMBOK][BRIDGE] ROUTED | Protocol=%s | Id=%s | Command=%s | Target=%s | Payload=%s"),
        *LastProtocol,
        *LastId,
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
            TEXT("[SAREMBOK][BRIDGE] QUEUED | Id=%s | Command=%s | Pending=%d"),
            *LastId,
            *LastCommand,
            PendingCommands.Num()
        );
    }
}

bool FSarembokMessageDispatcher::ExecuteCommand(const FString& Message)
{
    if (IsEngineExitRequested() || !GEngine)
    {
        return true;
    }

    UWorld* RuntimeWorld = nullptr;

    for (const FWorldContext& Context : GEngine->GetWorldContexts())
    {
        UWorld* CandidateWorld = Context.World();

        if (!CandidateWorld || CandidateWorld->IsUnreachable())
        {
            continue;
        }

        if (Context.WorldType == EWorldType::Game ||
            Context.WorldType == EWorldType::PIE)
        {
            RuntimeWorld = CandidateWorld;
            break;
        }
    }

    if (!RuntimeWorld)
    {
        UE_LOG(
            LogTemp,
            Display,
            TEXT("[SAREMBOK][BRIDGE] WAITING | No runtime game world available")
        );

        return false;
    }

    USarembokAvatarComponent* AvatarComponent = nullptr;
    USarembokAvatarController* AvatarController = nullptr;

    for (TActorIterator<AActor> It(RuntimeWorld); It; ++It)
    {
        if (!AvatarComponent)
        {
            AvatarComponent =
                It->FindComponentByClass<USarembokAvatarComponent>();
        }

        if (!AvatarController)
        {
            AvatarController =
                It->FindComponentByClass<USarembokAvatarController>();
        }

        if (AvatarComponent && AvatarController)
        {
            break;
        }
    }

    // Deterministic Fallback: Spawn avatar actor in world if components are missing
    if (!AvatarComponent || !AvatarController)
    {
        FActorSpawnParameters SpawnParams;
        SpawnParams.Name = FName(TEXT("SarembokRuntimeAvatarActor"));
        SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

        AActor* FallbackActor = RuntimeWorld->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
        if (FallbackActor)
        {
            if (!AvatarComponent)
            {
                AvatarComponent = NewObject<USarembokAvatarComponent>(FallbackActor, TEXT("SarembokAvatarComponent"));
                AvatarComponent->RegisterComponent();
            }
            if (!AvatarController)
            {
                AvatarController = NewObject<USarembokAvatarController>(FallbackActor, TEXT("SarembokAvatarController"));
                AvatarController->RegisterComponent();
            }
            UE_LOG(LogTemp, Display, TEXT("[SAREMBOK] Deterministic Fallback Avatar Created in Runtime World"));
        }
    }

    TWeakObjectPtr<USarembokAvatarComponent> WeakAvatarComponent(AvatarComponent);
    TWeakObjectPtr<USarembokAvatarController> WeakAvatarController(AvatarController);

    if (LastCommand.Equals(SarembokCommandConstants::Emotion, ESearchCase::IgnoreCase))
    {
        FString Emotion;

        TSharedPtr<FJsonObject> JsonObject;
        TSharedRef<TJsonReader<>> Reader =
            TJsonReaderFactory<>::Create(Message);

        if (FJsonSerializer::Deserialize(Reader, JsonObject) &&
            JsonObject.IsValid())
        {
            const TSharedPtr<FJsonObject>* PayloadObject = nullptr;

            if (JsonObject->TryGetObjectField(SarembokCommandConstants::KeyPayload, PayloadObject) &&
                PayloadObject &&
                PayloadObject->IsValid())
            {
                (*PayloadObject)->TryGetStringField(
                    SarembokCommandConstants::KeyState,
                    Emotion
                );
            }
        }

        if (!WeakAvatarController.IsValid())
        {
            UE_LOG(
                LogTemp,
                Display,
                TEXT("[SAREMBOK][AVATAR] Emotion command waiting for AvatarController")
            );

            return false;
        }

        if (Emotion.IsEmpty())
        {
            UE_LOG(
                LogTemp,
                Warning,
                TEXT("[SAREMBOK][AVATAR] Emotion command missing state payload")
            );

            return true;
        }

        WeakAvatarController->SetEmotion(Emotion);

        UE_LOG(
            LogTemp,
            Display,
            TEXT("[SAREMBOK][AVATAR] EMOTION_EXECUTED | Id=%s | Emotion=%s"),
            *LastId,
            *Emotion
        );

        return true;
    }

    if (LastCommand.Equals(SarembokCommandConstants::Speak, ESearchCase::IgnoreCase))
    {
        FString Text;
        FString Emotion;

        TSharedPtr<FJsonObject> JsonObject;
        TSharedRef<TJsonReader<>> Reader =
            TJsonReaderFactory<>::Create(Message);

        if (FJsonSerializer::Deserialize(Reader, JsonObject) &&
            JsonObject.IsValid())
        {
            const TSharedPtr<FJsonObject>* PayloadObject = nullptr;

            if (JsonObject->TryGetObjectField(SarembokCommandConstants::KeyPayload, PayloadObject) &&
                PayloadObject &&
                PayloadObject->IsValid())
            {
                (*PayloadObject)->TryGetStringField(
                    SarembokCommandConstants::KeyText,
                    Text
                );

                (*PayloadObject)->TryGetStringField(
                    SarembokCommandConstants::KeyEmotion,
                    Emotion
                );
            }
        }

        if (!WeakAvatarComponent.IsValid())
        {
            UE_LOG(
                LogTemp,
                Display,
                TEXT("[SAREMBOK][VOICE] Speak command waiting for AvatarComponent")
            );

            return false;
        }

        if (Text.IsEmpty())
        {
            UE_LOG(
                LogTemp,
                Warning,
                TEXT("[SAREMBOK][VOICE] Speak command missing text payload")
            );

            return true;
        }

        if (WeakAvatarController.IsValid() && !Emotion.IsEmpty())
        {
            WeakAvatarController->SetEmotion(Emotion);
        }

        WeakAvatarComponent->Speak(Text);

        UE_LOG(
            LogTemp,
            Display,
            TEXT("[SAREMBOK][VOICE] EXECUTED | Id=%s | Text=%s"),
            *LastId,
            *Text
        );

        return true;
    }

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][BRIDGE] Command received with no explicit executor: %s"),
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

    TArray<FString> CommandsToProcess =
        MoveTemp(PendingCommands);

    UE_LOG(
        LogTemp,
        Display,
        TEXT("[SAREMBOK][BRIDGE] COMMAND QUEUE CHECK | Pending=%d"),
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
            TEXT("[SAREMBOK][BRIDGE] COMMAND QUEUE WAITING | Pending=%d"),
            PendingCommands.Num()
        );
    }

    return true;
}

void FSarembokMessageDispatcher::ParseCommand(const FString& Message)
{
    LastProtocol.Empty();
    LastId.Empty();
    LastTimestamp.Empty();
    LastCommand.Empty();
    LastTarget.Empty();
    LastPayload.Empty();

    TSharedPtr<FJsonObject> JsonObject;

    TSharedRef<TJsonReader<>> Reader =
        TJsonReaderFactory<>::Create(Message);

    if (!FJsonSerializer::Deserialize(Reader, JsonObject) ||
        !JsonObject.IsValid())
    {
        UE_LOG(
            LogTemp,
            Error,
            TEXT("[SAREMBOK][BRIDGE] Invalid command JSON")
        );

        return;
    }

    JsonObject->TryGetStringField(TEXT("protocol"), LastProtocol);
    JsonObject->TryGetStringField(TEXT("id"), LastId);
    JsonObject->TryGetStringField(TEXT("timestamp"), LastTimestamp);

    if (LastProtocol.IsEmpty())
    {
        LastProtocol = TEXT("legacy.v0");
    }

    if (LastId.IsEmpty())
    {
        LastId = TEXT("cmd-legacy");
    }

    JsonObject->TryGetStringField(
        SarembokCommandConstants::KeyCommand,
        LastCommand
    );

    JsonObject->TryGetStringField(
        SarembokCommandConstants::KeyTarget,
        LastTarget
    );

    const TSharedPtr<FJsonObject>* PayloadObject = nullptr;

    if (JsonObject->TryGetObjectField(SarembokCommandConstants::KeyPayload, PayloadObject) &&
        PayloadObject &&
        PayloadObject->IsValid())
    {
        TSharedRef<TJsonWriter<>> Writer =
            TJsonWriterFactory<>::Create(&LastPayload);

        FJsonSerializer::Serialize(
            PayloadObject->ToSharedRef(),
            Writer
        );

        Writer->Close();
    }

    if (LastCommand.IsEmpty())
    {
        UE_LOG(
            LogTemp,
            Warning,
            TEXT("[SAREMBOK][BRIDGE] Command received without command field")
        );
    }
}

FString FSarembokMessageDispatcher::GetLastCommand() const
{
    return LastCommand;
}

FString FSarembokMessageDispatcher::GetLastProtocol() const
{
    return LastProtocol;
}

FString FSarembokMessageDispatcher::GetLastCorrelationId() const
{
    return LastId;
}
