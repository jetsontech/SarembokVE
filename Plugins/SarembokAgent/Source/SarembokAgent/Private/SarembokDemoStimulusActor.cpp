#include "SarembokDemoStimulusActor.h"

ASarembokDemoStimulusActor::ASarembokDemoStimulusActor()
{
    PrimaryActorTick.bCanEverTick = false;
    Tags.Add(FName("SarembokDemoStimulusActor"));
}

void ASarembokDemoStimulusActor::BeginPlay()
{
    Super::BeginPlay();
    UE_LOG(LogTemp, Display, TEXT("[SAREMBOK][DEMO] STIMULUS_ACTOR_SPAWNED Actor=SarembokDemoStimulusActor"));
}
