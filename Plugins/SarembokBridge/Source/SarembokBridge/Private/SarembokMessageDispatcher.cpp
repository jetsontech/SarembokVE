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
        TEXT("Sarembok Command: %s Target: %s Payload: %s"),
        *LastCommand,
        *LastTarget,
        *LastPayload
    );
}

void FSarembokMessageDispatcher::ParseCommand(const FString& Message)
{
    TSharedPtr<FJsonObject> JsonObject;

    TSharedRef<TJsonReader<>> Reader =
        TJsonReaderFactory<>::Create(Message);

    if (!FJsonSerializer::Deserialize(Reader, JsonObject) ||
        !JsonObject.IsValid())
    {
        LastCommand.Empty();
        LastTarget.Empty();
        LastPayload.Empty();
        return;
    }

    JsonObject->TryGetStringField(TEXT("command"), LastCommand);
    JsonObject->TryGetStringField(TEXT("target"), LastTarget);

    const TSharedPtr<FJsonObject>* PayloadObject = nullptr;

    if (JsonObject->TryGetObjectField(TEXT("payload"), PayloadObject) &&
        PayloadObject != nullptr &&
        PayloadObject->IsValid())
    {
        LastPayload.Empty();

        for (const TPair<FString, TSharedPtr<FJsonValue>>& Field :
             (*PayloadObject)->Values)
        {
            const FString Key = Field.Key;
            const FString Value =
                Field.Value.IsValid()
                    ? Field.Value->AsString()
                    : FString();

            LastPayload += Key;
            LastPayload += TEXT("=");
            LastPayload += Value;
            LastPayload += TEXT(";");
        }
    }
    else
    {
        LastPayload.Empty();
    }
}

FString FSarembokMessageDispatcher::GetLastCommand() const
{
    return LastCommand;
}
