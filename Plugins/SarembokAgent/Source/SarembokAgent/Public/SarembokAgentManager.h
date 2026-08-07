#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokAgentManager.generated.h"

USTRUCT(BlueprintType)
struct FSarembokTask
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite)
    FString TaskId;

    UPROPERTY(BlueprintReadWrite)
    FString Intent;

    UPROPERTY(BlueprintReadWrite)
    FString Payload;
};

UCLASS()
class SAREMBOKAGENT_API USarembokAgentManager : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok Agent")
    FString SubmitTask(const FSarembokTask& Task);

    UFUNCTION(BlueprintCallable, Category="Sarembok Agent")
    FString GetAgentState() const;

private:
    FString CurrentState;
};
