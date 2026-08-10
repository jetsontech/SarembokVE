// ============================================================
// SarembokSocialDemoController.cpp
// ============================================================

#include "SarembokSocialDemoController.h"
#include "SarembokAgentManager.h"
#include "SarembokConversationManager.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

ASarembokSocialDemoController::ASarembokSocialDemoController()
{
    PrimaryActorTick.bCanEverTick = false;
}

void ASarembokSocialDemoController::BeginPlay()
{
    Super::BeginPlay();

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][SOCIAL_DEMO] Controller Initialized"));
}

void ASarembokSocialDemoController::TriggerScenarioA_UserEntry()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][SOCIAL_DEMO] SCENARIO_A_START | User Entry & Greeting"));

    if (UWorld* World = GetWorld())
    {
        if (UGameInstance* GI = World->GetGameInstance())
        {
            if (USarembokConversationManager* Conv = GI->GetSubsystem<USarembokConversationManager>())
            {
                Conv->UpdateUserPresence(true, 184.2f);
            }
            if (USarembokAgentManager* Agent = GI->GetSubsystem<USarembokAgentManager>())
            {
                FSarembokGoal Goal;
                Goal.GoalId = TEXT("greet.user");
                Goal.Description = TEXT("Greet user entering FOV");
                Goal.Priority = 90;
                Agent->PushGoal(Goal);
            }
        }
    }
}

void ASarembokSocialDemoController::TriggerScenarioB_UserQuestion(const FString& Question)
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][SOCIAL_DEMO] SCENARIO_B_START | Question: %s"), *Question);

    if (UWorld* World = GetWorld())
    {
        if (UGameInstance* GI = World->GetGameInstance())
        {
            if (USarembokConversationManager* Conv = GI->GetSubsystem<USarembokConversationManager>())
            {
                Conv->ProcessUserTurn(Question);
            }
            if (USarembokAgentManager* Agent = GI->GetSubsystem<USarembokAgentManager>())
            {
                FSarembokGoal Goal;
                Goal.GoalId = TEXT("answer.user");
                Goal.Description = Question;
                Goal.Priority = 80;
                Agent->PushGoal(Goal);
            }
        }
    }
}

void ASarembokSocialDemoController::TriggerScenarioC_LLMFailure()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][SOCIAL_DEMO] SCENARIO_C_START | LLM Timeout & Safety Fallback"));

    if (UWorld* World = GetWorld())
    {
        if (UGameInstance* GI = World->GetGameInstance())
        {
            if (USarembokAgentManager* Agent = GI->GetSubsystem<USarembokAgentManager>())
            {
                Agent->SetLLMMode(true);
                FSarembokGoal Goal;
                Goal.GoalId = TEXT("complex.query");
                Goal.Description = TEXT("Trigger LLM fallback path");
                Goal.Priority = 70;
                Agent->PushGoal(Goal);
            }
        }
    }
}

void ASarembokSocialDemoController::TriggerScenarioD_GoalReplanning()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][SOCIAL_DEMO] SCENARIO_D_START | Goal Failure & Replanning Recovery"));

    if (UWorld* World = GetWorld())
    {
        if (UGameInstance* GI = World->GetGameInstance())
        {
            if (USarembokAgentManager* Agent = GI->GetSubsystem<USarembokAgentManager>())
            {
                Agent->SetSimulateActionFailure(true);
                FSarembokGoal Goal;
                Goal.GoalId = TEXT("demo.observe.respond");
                Goal.Description = TEXT("Demonstrate replanning recovery");
                Goal.Priority = 60;
                Agent->PushGoal(Goal);
            }
        }
    }
}
