#include "SarembokMessageDispatcher.h"
#include "SarembokCommandBus.h"

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
        TEXT("Sarembok Command: %s Target: %s Payload: %s"),
        *LastCommand,
        *LastTarget,
        *LastPayload
    );
}

void FSarembokMessageDispatcher::ParseCommand(const FString& Message)
{
    TSharedPtr<FJsonObject> JsonObject;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);

    if (!FJsonSerializer::Deserialize(Reader, JsonObject) || !JsonObject.IsValid())
    {
        LastCommand.Empty();
        LastTarget.Empty();
        LastPayload.Empty();
        return;
    }

    if (!JsonObject->TryGetStringField(TEXT("command"), LastCommand))
    {
        LastCommand.Empty();
    }

    if (!JsonObject->TryGetStringField(TEXT("target"), LastTarget))
    {
        LastTarget.Empty();
    }

    const TSharedPtr<FJsonObject>* PayloadObject = nullptr;
    LastPayload.Empty();

    if (JsonObject->TryGetObjectField(TEXT("payload"), PayloadObject) &&
        PayloadObject != nullptr &&
        PayloadObject->IsValid())
    {
        TSharedRef<TJsonWriter<>> Writer =
            TJsonWriterFactory<>::Create(&LastPayload);
        FJsonSerializer::Serialize(PayloadObject->ToSharedRef(), Writer);
        Writer->Close();
    }

    if (LastCommand.IsEmpty())
    {
        return;
    }

    FSarembokCommand Command;
    Command.Command = LastCommand;
    Command.Target = LastTarget;
    Command.Payload = LastPayload;

    FSarembokCommandBus::Get().Dispatch(Command);
}

FString FSarembokMessageDispatcher::GetLastCommand() const
{
    return LastCommand;
}
