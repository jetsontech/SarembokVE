#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "SarembokCommandRouter.generated.h"

USTRUCT(BlueprintType)
struct SAREMBOKBRIDGE_API FSarembokCommand
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite)
    FString Command;

    UPROPERTY(BlueprintReadWrite)
    FString Target;

    UPROPERTY(BlueprintReadWrite)
    FString Payload;
};

UCLASS(Blueprintable)
class SAREMBOKBRIDGE_API USarembokCommandRouter : public UObject
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category="Sarembok Bridge")
    bool RouteCommand(const FSarembokCommand& Command);

    UFUNCTION(BlueprintCallable, Category="Sarembok Bridge")
    FString GetLastCommand() const;

private:
    FString LastCommand;
};
