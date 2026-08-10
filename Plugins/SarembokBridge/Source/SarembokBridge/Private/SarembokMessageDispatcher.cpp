#include "SarembokMessageDispatcher.h"

#include "Dom/JsonObject.h"
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
