#include "SarembokMessageRouter.h"

FSarembokMessageRouter& FSarembokMessageRouter::Get()
{
    static FSarembokMessageRouter Instance;
    return Instance;
}

void FSarembokMessageRouter::RegisterHandler(const FString& EventName, FSarembokMessageHandler Handler)
{
    Handlers.Add(EventName, Handler);
}

void FSarembokMessageRouter::Dispatch(const FSarembokMessage& Message)
{
    if (FSarembokMessageHandler* Handler = Handlers.Find(Message.Event))
    {
        Handler->ExecuteIfBound(Message);
    }
}
