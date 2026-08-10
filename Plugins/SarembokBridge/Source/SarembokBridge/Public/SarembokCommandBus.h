#pragma once

#include "CoreMinimal.h"
#include "SarembokCommandRouter.h"

DECLARE_MULTICAST_DELEGATE_OneParam(FSarembokCommandDelegate, const FSarembokCommand&);

class SAREMBOKBRIDGE_API FSarembokCommandBus
{
public:
    static FSarembokCommandBus& Get();

    void Dispatch(const FSarembokCommand& Command);
    FDelegateHandle Subscribe(const FSarembokCommandDelegate::FDelegate& Handler);
    void Unsubscribe(FDelegateHandle Handle);

    FSarembokCommandDelegate OnCommand;

private:
    FSarembokCommandBus() = default;
};
