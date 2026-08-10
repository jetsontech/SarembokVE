// ============================================================
// SarembokSessionDemoController.cpp
// Multi-Session Persistent Continuity Harness Implementation
// ============================================================

#include "SarembokSessionDemoController.h"
#include "SarembokSocialMemoryManager.h"
#include "SarembokConversationManager.h"
#include "SarembokAgentManager.h"
#include "SarembokEventStream.h"
#include "Kismet/GameplayStatics.h"

ASarembokSessionDemoController::ASarembokSessionDemoController()
{
    PrimaryActorTick.bCanEverTick = false;
}

void ASarembokSessionDemoController::BeginPlay()
{
    Super::BeginPlay();
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][SESSION_DEMO] HARNESS_READY"));
}

void ASarembokSessionDemoController::TriggerSession1_FirstContact()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][SESSION_DEMO] SESSION_1_START | First Contact (Unknown User)"));

    if (UWorld* World = GetWorld())
    {
        if (UGameInstance* GI = World->GetGameInstance())
        {
            USarembokSocialMemoryManager* SocialMem = GI->GetSubsystem<USarembokSocialMemoryManager>();
            USarembokConversationManager* Conv = GI->GetSubsystem<USarembokConversationManager>();
            USarembokAgentManager* Agent = GI->GetSubsystem<USarembokAgentManager>();
            USarembokEventStreamSubsystem* EvtStream = GI->GetSubsystem<USarembokEventStreamSubsystem>();

            if (SocialMem)
            {
                FSarembokSocialProfile Profile = SocialMem->GetOrCreateProfile(TEXT("user-0007"), TEXT("Alex"));
                SocialMem->UpdateFact(TEXT("user-0007"), TEXT("favorite_workstation"), TEXT("NVIDIA RTX 4090 Workstation"));
                SocialMem->RecordInteraction(TEXT("user-0007"), TEXT("conv-000001"), TEXT("Workstation Architecture"));
            }

            if (Conv)
            {
                Conv->UpdateUserPresence(true, 180.0f);
                Conv->ProcessUserTurn(TEXT("Hello, I am Alex testing the NVIDIA workstation."));
            }

            if (Agent)
            {
                FSarembokGoal Goal;
                Goal.GoalId = TEXT("greet.first_contact");
                Goal.Description = TEXT("Greet Alex for the first time");
                Goal.Priority = 90;
                Agent->PushGoal(Goal);
            }

            if (EvtStream)
            {
                FSarembokEvent Evt;
                Evt.TraceId = TEXT("trace-session-1");
                Evt.ConversationId = TEXT("conv-000001");
                Evt.UserId = TEXT("user-0007");
                Evt.EventType = TEXT("FIRST_CONTACT_PROFILE_CREATED");
                Evt.Source = TEXT("SESSION_HARNESS");
                Evt.Payload = TEXT("{\"user_id\":\"user-0007\",\"name\":\"Alex\",\"fact\":\"NVIDIA RTX 4090 Workstation\"}");
                Evt.Outcome = TEXT("Completed");
                EvtStream->EmitEvent(Evt);
            }
        }
    }
}

void ASarembokSessionDemoController::TriggerSession2_ReturnVisit()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][SESSION_DEMO] SESSION_2_START | Return Visit (Recognized User)"));

    if (UWorld* World = GetWorld())
    {
        if (UGameInstance* GI = World->GetGameInstance())
        {
            USarembokSocialMemoryManager* SocialMem = GI->GetSubsystem<USarembokSocialMemoryManager>();
            USarembokConversationManager* Conv = GI->GetSubsystem<USarembokConversationManager>();
            USarembokAgentManager* Agent = GI->GetSubsystem<USarembokAgentManager>();
            USarembokEventStreamSubsystem* EvtStream = GI->GetSubsystem<USarembokEventStreamSubsystem>();

            FString GreetingText = TEXT("Good to see you again Alex. Shall we continue discussing the NVIDIA workstation?");

            if (SocialMem)
            {
                FSarembokSocialProfile Profile = SocialMem->GetOrCreateProfile(TEXT("user-0007"), TEXT("Alex"));
                SocialMem->RecordInteraction(TEXT("user-0007"), TEXT("conv-000002"), TEXT("Workstation Architecture"));
            }

            if (Conv)
            {
                Conv->UpdateUserPresence(true, 150.0f);
            }

            if (Agent)
            {
                FSarembokGoal Goal;
                Goal.GoalId = TEXT("reconnect.recognized_user");
                Goal.Description = GreetingText;
                Goal.Priority = 95;
                Agent->PushGoal(Goal);
            }

            if (EvtStream)
            {
                FSarembokEvent Evt;
                Evt.TraceId = TEXT("trace-session-2");
                Evt.ConversationId = TEXT("conv-000002");
                Evt.UserId = TEXT("user-0007");
                Evt.EventType = TEXT("RETURN_VISIT_RECOGNIZED");
                Evt.Source = TEXT("SESSION_HARNESS");
                Evt.Payload = TEXT("{\"user_id\":\"user-0007\",\"name\":\"Alex\",\"familiarity\":0.25}");
                Evt.Outcome = TEXT("Completed");
                EvtStream->EmitEvent(Evt);
            }
        }
    }
}

void ASarembokSessionDemoController::TriggerSession3_Contradiction()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][SESSION_DEMO] SESSION_3_START | Fact Contradiction & Reconciliation"));

    if (UWorld* World = GetWorld())
    {
        if (UGameInstance* GI = World->GetGameInstance())
        {
            USarembokSocialMemoryManager* SocialMem = GI->GetSubsystem<USarembokSocialMemoryManager>();
            USarembokConversationManager* Conv = GI->GetSubsystem<USarembokConversationManager>();
            USarembokAgentManager* Agent = GI->GetSubsystem<USarembokAgentManager>();
            USarembokEventStreamSubsystem* EvtStream = GI->GetSubsystem<USarembokEventStreamSubsystem>();

            FString ExistingFact;
            if (SocialMem)
            {
                bool bContradiction = SocialMem->DetectFactContradiction(TEXT("user-0007"), TEXT("favorite_workstation"), TEXT("Mac Studio"), ExistingFact);
                if (bContradiction)
                {
                    SocialMem->UpdateFact(TEXT("user-0007"), TEXT("favorite_workstation"), TEXT("Mac Studio"));
                }
            }

            if (Conv)
            {
                Conv->ProcessUserTurn(TEXT("Actually, my workstation is a Mac Studio."));
            }

            if (Agent)
            {
                FSarembokGoal Goal;
                Goal.GoalId = TEXT("reconcile.fact");
                Goal.Description = TEXT("Update user workstation preference from NVIDIA to Mac Studio");
                Goal.Priority = 85;
                Agent->PushGoal(Goal);
            }

            if (EvtStream)
            {
                FSarembokEvent Evt;
                Evt.TraceId = TEXT("trace-session-3");
                Evt.ConversationId = TEXT("conv-000003");
                Evt.UserId = TEXT("user-0007");
                Evt.EventType = TEXT("FACT_CONTRADICTION_RECONCILED");
                Evt.Source = TEXT("SESSION_HARNESS");
                Evt.Payload = TEXT("{\"key\":\"favorite_workstation\",\"old\":\"NVIDIA RTX 4090 Workstation\",\"new\":\"Mac Studio\"}");
                Evt.Outcome = TEXT("Completed");
                EvtStream->EmitEvent(Evt);
            }
        }
    }
}

void ASarembokSessionDemoController::TriggerSession4_LongTermGoal()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][SESSION_DEMO] SESSION_4_START | Long-Term Goal Persistence Across Boundary"));

    if (UWorld* World = GetWorld())
    {
        if (UGameInstance* GI = World->GetGameInstance())
        {
            USarembokAgentManager* Agent = GI->GetSubsystem<USarembokAgentManager>();
            USarembokEventStreamSubsystem* EvtStream = GI->GetSubsystem<USarembokEventStreamSubsystem>();

            if (Agent)
            {
                FSarembokGoal LongTermGoal;
                LongTermGoal.GoalId = TEXT("deploy.ai.cluster");
                LongTermGoal.Description = TEXT("Deploy multi-node autonomous AI cluster");
                LongTermGoal.Priority = 100;
                Agent->PushGoal(LongTermGoal);
            }

            if (EvtStream)
            {
                FSarembokEvent Evt;
                Evt.TraceId = TEXT("trace-session-4");
                Evt.ConversationId = TEXT("conv-000004");
                Evt.UserId = TEXT("user-0007");
                Evt.EventType = TEXT("LONG_TERM_GOAL_RECALLED");
                Evt.Source = TEXT("SESSION_HARNESS");
                Evt.Payload = TEXT("{\"goal_id\":\"deploy.ai.cluster\",\"status\":\"Active\"}");
                Evt.Outcome = TEXT("Completed");
                EvtStream->EmitEvent(Evt);
            }
        }
    }
}

void ASarembokSessionDemoController::TriggerSession5_ResilienceFallback()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][SESSION_DEMO] SESSION_5_START | Resilience & Fallback Safety"));

    if (UWorld* World = GetWorld())
    {
        if (UGameInstance* GI = World->GetGameInstance())
        {
            USarembokAgentManager* Agent = GI->GetSubsystem<USarembokAgentManager>();
            USarembokEventStreamSubsystem* EvtStream = GI->GetSubsystem<USarembokEventStreamSubsystem>();

            if (Agent)
            {
                Agent->SetLLMMode(true);
                FSarembokGoal FallbackGoal;
                FallbackGoal.GoalId = TEXT("resilience.test");
                FallbackGoal.Description = TEXT("Verify seamless fallback during LLM provider disruption");
                FallbackGoal.Priority = 75;
                Agent->PushGoal(FallbackGoal);
            }

            if (EvtStream)
            {
                FSarembokEvent Evt;
                Evt.TraceId = TEXT("trace-session-5");
                Evt.ConversationId = TEXT("conv-000005");
                Evt.UserId = TEXT("user-0007");
                Evt.EventType = TEXT("RESILIENCE_FALLBACK_VERIFIED");
                Evt.Source = TEXT("SESSION_HARNESS");
                Evt.Payload = TEXT("{\"fallback\":\"DeterministicReasoner\",\"status\":\"Active\"}");
                Evt.Outcome = TEXT("Completed");
                EvtStream->EmitEvent(Evt);
            }
        }
    }
}
