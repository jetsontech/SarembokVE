// ============================================================
// SarembokSocialDemoController.h
// Social & Behavioral Scenario Demonstration Harness Actor
// ============================================================

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SarembokSocialDemoController.generated.h"

UCLASS(ClassGroup=(Sarembok), meta=(BlueprintSpawnableComponent))
class SAREMBOKAGENT_API ASarembokSocialDemoController : public AActor
{
    GENERATED_BODY()

public:

    ASarembokSocialDemoController();

    virtual void BeginPlay() override;

    UFUNCTION(BlueprintCallable, Category="Sarembok|SocialDemo")
    void TriggerScenarioA_UserEntry();

    UFUNCTION(BlueprintCallable, Category="Sarembok|SocialDemo")
    void TriggerScenarioB_UserQuestion(const FString& Question = TEXT("Where is the AI workstation located?"));

    UFUNCTION(BlueprintCallable, Category="Sarembok|SocialDemo")
    void TriggerScenarioC_LLMFailure();

    UFUNCTION(BlueprintCallable, Category="Sarembok|SocialDemo")
    void TriggerScenarioD_GoalReplanning();
};
