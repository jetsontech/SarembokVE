#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "SarembokOrchestrator.generated.h"

UCLASS(Blueprintable)
class SAREMBOKAGENT_API USarembokOrchestrator : public UObject
{
    GENERATED_BODY()

public:

    UFUNCTION(BlueprintCallable, Category="Sarembok AI")
    void StartInteraction(const FString& Context);

    UFUNCTION(BlueprintCallable, Category="Sarembok AI")
    FString GetCurrentOperation() const;

private:

    FString CurrentOperation;
};
