#pragma once

#include "CoreMinimal.h"

class FSarembokMessageDispatcher
{
public:

    FSarembokMessageDispatcher();
    ~FSarembokMessageDispatcher();

    void DispatchMessage(const FString& Message);

    FString GetLastCommand() const;

private:

    void ParseCommand(const FString& Message);

    FString LastCommand;
    FString LastTarget;
    FString LastPayload;
};
