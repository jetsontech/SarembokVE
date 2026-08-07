#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "SarembokAutonomousLoop.generated.h"

UENUM(BlueprintType)
enum class ESarembokLoopState : uint8
{
    Idle,
    Perceiving,
    Planning,
    Acting,
    Responding
};

UCLASS(Blueprintable)
class SAREMBOKAGENT_API USarembokAutonomousLoop : public UObject
{
    GENERATED_BODY()

public:

    UFUNCTION(BlueprintCallable, Category="Sarembok AI")
    void StartCycle(const FString& InputContext);

    UFUNCTION(BlueprintCallable, Category="Sarembok AI")
    ESarembokLoopState GetLoopState() const;

private:

    ESarembokLoopState CurrentState = ESarembokLoopState::Idle;
    FString CurrentContext;
};
