#include "SarembokCommandRouter.h"

bool USarembokCommandRouter::RouteCommand(const FSarembokCommand& Command)
{
    LastCommand = FString::Printf(
        TEXT("%s:%s:%s"),
        *Command.Command,
        *Command.Target,
        *Command.Payload
    );

    UE_LOG(LogTemp, Log,
        TEXT("Sarembok Command Routed: %s"),
        *LastCommand);

    return true;
}

FString USarembokCommandRouter::GetLastCommand() const
{
    return LastCommand;
}
