#pragma once

#include "CoreMinimal.h"
#include "SarembokMessage.h"

DECLARE_DELEGATE_OneParam(FSarembokMessageHandler, const FSarembokMessage&);

class SAREMBOKBRIDGE_API FSarembokMessageRouter
{
public:

    static FSarembokMessageRouter& Get();

    void RegisterHandler(const FString& EventName, FSarembokMessageHandler Handler);
    void Dispatch(const FSarembokMessage& Message);

private:

    TMap<FString, FSarembokMessageHandler> Handlers;
};
