#include "SarembokBridgeTestActor.h"
#include "SarembokBridgeModule.h"

ASarembokBridgeTestActor::ASarembokBridgeTestActor()
{
    PrimaryActorTick.bCanEverTick = false;
    RootScene = CreateDefaultSubobject<USceneComponent>(TEXT("RootScene"));
    RootComponent = RootScene;
}

void ASarembokBridgeTestActor::BeginPlay()
{
    Super::BeginPlay();

    UE_LOG(LogTemp, Display, TEXT("SarembokBridgeTestActor has begun play."));
    UE_LOG(LogTemp, Display, TEXT("SarembokBridge module loaded: %s"), *FString(TEXT("true")));
}
