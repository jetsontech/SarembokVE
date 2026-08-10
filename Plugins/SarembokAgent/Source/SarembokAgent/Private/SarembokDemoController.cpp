#include "SarembokDemoController.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

ASarembokDemoController::ASarembokDemoController()
{
    PrimaryActorTick.bCanEverTick = false;
    SpawnedStimulusActor = nullptr;
}

void ASarembokDemoController::BeginPlay()
{
    Super::BeginPlay();
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][DEMO] CONTROLLER_INITIALIZED"));
}

FSarembokGoal ASarembokDemoController::CreateDemoGoal()
{
    FSarembokGoal DemoGoal;
    DemoGoal.GoalId = TEXT("demo.observe.respond");
    DemoGoal.Description = TEXT("Observe the environment and respond when a new actor appears.");
    DemoGoal.Priority = 80;
    DemoGoal.TargetState = TEXT("environment_observed_and_response_completed");
    DemoGoal.Progress = 0.0f;
    DemoGoal.Status = TEXT("Active");

    if (UGameInstance* GI = GetGameInstance())
    {
        if (USarembokAgentManager* AgentMgr = GI->GetSubsystem<USarembokAgentManager>())
        {
            AgentMgr->PushGoal(DemoGoal);
        }
    }

    UE_LOG(LogTemp, Display,
        TEXT("[SAREMBOK][DEMO] GOAL_CREATED Id=%s Description=\"%s\" Priority=%d TargetState=\"%s\""),
        *DemoGoal.GoalId, *DemoGoal.Description, DemoGoal.Priority, *DemoGoal.TargetState);

    return DemoGoal;
}

void ASarembokDemoController::ClearDemoGoals()
{
    if (UGameInstance* GI = GetGameInstance())
    {
        if (USarembokAgentManager* AgentMgr = GI->GetSubsystem<USarembokAgentManager>())
        {
            FSarembokGoal Popped;
            while (AgentMgr->PopGoal(Popped))
            {
                // Clearing goals
            }
        }
    }
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][DEMO] GOALS_CLEARED"));
}

FSarembokGoal ASarembokDemoController::GetCurrentGoal() const
{
    if (UGameInstance* GI = GetGameInstance())
    {
        if (USarembokAgentManager* AgentMgr = GI->GetSubsystem<USarembokAgentManager>())
        {
            return AgentMgr->GetActiveGoal();
        }
    }
    return FSarembokGoal();
}

FSarembokIntent ASarembokDemoController::GetCurrentIntent() const
{
    return LastIntentCache;
}

float ASarembokDemoController::GetCurrentConfidence() const
{
    return LastIntentCache.Confidence;
}

FString ASarembokDemoController::GetCurrentAgentState() const
{
    if (UGameInstance* GI = GetGameInstance())
    {
        if (USarembokAgentManager* AgentMgr = GI->GetSubsystem<USarembokAgentManager>())
        {
            return AgentMgr->GetAgentState();
        }
    }
    return TEXT("UNKNOWN");
}

ASarembokDemoStimulusActor* ASarembokDemoController::SpawnDemoStimulusActor()
{
    UWorld* World = GetWorld();
    if (!World)
    {
        return nullptr;
    }

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(TEXT("SarembokDemoStimulusActor"));
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

    FVector Location(100.0f, 100.0f, 0.0f);
    FRotator Rotation = FRotator::ZeroRotator;

    SpawnedStimulusActor = World->SpawnActor<ASarembokDemoStimulusActor>(ASarembokDemoStimulusActor::StaticClass(), Location, Rotation, SpawnParams);

    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][DEMO] STIMULUS_SPAWNED Actor=SarembokDemoStimulusActor Location=(100,100,0)"));
    return SpawnedStimulusActor;
}

void ASarembokDemoController::InjectDemoFailure()
{
    if (UGameInstance* GI = GetGameInstance())
    {
        if (USarembokAgentManager* AgentMgr = GI->GetSubsystem<USarembokAgentManager>())
        {
            AgentMgr->SetSimulateActionFailure(true);
            UE_LOG(LogTemp, Warning, TEXT("[SAREMBOK][DEMO] FAILURE_INJECTED Target=NextActionExecution"));

            FString OutCmd;
            AgentMgr->RunAutonomousLoop(OutCmd);
        }
    }
}

void ASarembokDemoController::StartAutonomousDemo()
{
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][DEMO] START_AUTONOMOUS_DEMO"));

    // 1. Create and push goal
    CreateDemoGoal();

    // 2. Spawn stimulus actor
    SpawnDemoStimulusActor();

    // 3. Trigger autonomous tick loop on agent manager
    if (UGameInstance* GI = GetGameInstance())
    {
        if (USarembokAgentManager* AgentMgr = GI->GetSubsystem<USarembokAgentManager>())
        {
            FString OutCmd;
            AgentMgr->RunAutonomousLoop(OutCmd);
        }
    }
}
