
// ============================================================
// SarembokAvatarManager.cpp
// Sarembok Autonomous AI Virtual Entity Platform
// ============================================================

#include "SarembokAvatarManager.h"


USarembokAvatarManager::USarembokAvatarManager()
{
    CurrentState = ESarembokAvatarState::Uninitialized;
}



void USarembokAvatarManager::InitializeAvatar()
{
    CurrentState = ESarembokAvatarState::Ready;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Avatar Initialized")
    );
}



void USarembokAvatarManager::ShutdownAvatar()
{
    CurrentState = ESarembokAvatarState::Disabled;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Sarembok Avatar Shutdown")
    );
}



void USarembokAvatarManager::SetAvatarState(
    ESarembokAvatarState NewState
)
{
    CurrentState = NewState;
}



ESarembokAvatarState 
USarembokAvatarManager::GetAvatarState() const
{
    return CurrentState;
}



void USarembokAvatarManager::TriggerExpression(
    FString ExpressionName
)
{
    UE_LOG(
        LogTemp,
        Display,
        TEXT("Avatar Expression: %s"),
        *ExpressionName
    );
}



void USarembokAvatarManager::SynchronizeVoice(
    FString AudioReference
)
{
    CurrentState = ESarembokAvatarState::Speaking;

    UE_LOG(
        LogTemp,
        Display,
        TEXT("Voice Sync: %s"),
        *AudioReference
    );
}

