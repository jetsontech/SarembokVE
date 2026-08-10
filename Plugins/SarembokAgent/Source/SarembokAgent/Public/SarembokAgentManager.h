#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "SarembokAgentManager.generated.h"

USTRUCT(BlueprintType)
struct FSarembokTask
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString TaskId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
    FString Intent;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sarembok Agent")
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

    UFUNCTION(BlueprintPure, Category="Sarembok Agent")
    FString GetAgentState() const;

    UFUNCTION(BlueprintPure, Category="Sarembok Agent")
    FSarembokTask GetActiveTask() const;

    UFUNCTION(BlueprintCallable, Category="Sarembok Agent")
    void CancelCurrentTask();

private:

    FString CurrentState;
    FSarembokTask ActiveTask;
};
