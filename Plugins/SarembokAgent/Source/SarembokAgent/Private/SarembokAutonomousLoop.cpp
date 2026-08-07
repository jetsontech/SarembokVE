#include "SarembokAutonomousLoop.h"

void USarembokAutonomousLoop::StartCycle(const FString& InputContext)
{
    CurrentContext = InputContext;

    CurrentState = ESarembokLoopState::Perceiving;
    UE_LOG(LogTemp, Log, TEXT("Sarembok Loop: Perceiving - %s"), *CurrentContext);

    CurrentState = ESarembokLoopState::Planning;
    UE_LOG(LogTemp, Log, TEXT("Sarembok Loop: Planning"));

    CurrentState = ESarembokLoopState::Acting;
    UE_LOG(LogTemp, Log, TEXT("Sarembok Loop: Acting"));

    CurrentState = ESarembokLoopState::Responding;
    UE_LOG(LogTemp, Log, TEXT("Sarembok Loop: Responding"));

    CurrentState = ESarembokLoopState::Idle;
}

ESarembokLoopState USarembokAutonomousLoop::GetLoopState() const
{
    return CurrentState;
}
