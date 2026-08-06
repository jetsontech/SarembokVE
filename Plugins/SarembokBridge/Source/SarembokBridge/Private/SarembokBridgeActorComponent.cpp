#include "SarembokBridgeActorComponent.h"

USarembokBridgeActorComponent::USarembokBridgeActorComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void USarembokBridgeActorComponent::BeginPlay()
{
    Super::BeginPlay();

    UE_LOG(LogTemp, Display, TEXT("SarembokBridgeActorComponent initialized."));
}
