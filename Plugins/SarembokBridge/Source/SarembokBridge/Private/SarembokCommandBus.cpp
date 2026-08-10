#include "SarembokCommandBus.h"

FSarembokCommandBus& FSarembokCommandBus::Get()
{
    static FSarembokCommandBus Instance;
    return Instance;
}

void FSarembokCommandBus::Dispatch(const FSarembokCommand& Command)
{
    OnCommand.Broadcast(Command);
}

FDelegateHandle FSarembokCommandBus::Subscribe(const FSarembokCommandDelegate::FDelegate& Handler)
{
    return OnCommand.Add(Handler);
}

void FSarembokCommandBus::Unsubscribe(FDelegateHandle Handle)
{
    OnCommand.Remove(Handle);
}
