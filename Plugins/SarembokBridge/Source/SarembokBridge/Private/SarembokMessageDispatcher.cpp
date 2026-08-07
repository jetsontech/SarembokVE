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

    UE_LOG(LogTemp, Display,
        TEXT("Sarembok Command: %s Target: %s Payload: %s"),
        *LastCommand,
        *LastTarget,
        *LastPayload);
}

void FSarembokMessageDispatcher::ParseCommand(const FString& Message)
{
    TSharedPtr<FJsonObject> JsonObject;

    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);

    if (FJsonSerializer::Deserialize(Reader, JsonObject) && JsonObject.IsValid())
    {
        JsonObject->TryGetStringField(TEXT("command"), LastCommand);
        JsonObject->TryGetStringField(TEXT("target"), LastTarget);

        const TSharedPtr<FJsonObject>* PayloadObject;
        if (JsonObject->TryGetObjectField(TEXT("payload"), PayloadObject))
        {
            LastPayload.Empty();
            for (const auto& Field : (*PayloadObject)->Values)
            {
                LastPayload += Field.Key + TEXT("=") + Field.Value->AsString() + TEXT(";");
            }
        }
    }
}

FString FSarembokMessageDispatcher::GetLastCommand() const
{
    return LastCommand;
}
